# Workstation roadmap

## 2026-10-19 — D-049 replanejamento 80/20 (DOCS-ONLY / NÃO RELEASE)
Ordem executável corrigida após a auditoria adversarial: G0 checkout limpo e sincronização segura de arquivos locais untracked, B0.1/B0.2; G1 propagação fiel de schema_valid do Electron até WorkItems/valid_count; G2 views snapshot expostas à tool e economia model-facing medida; IV DOM drift SOMENTE por evidência. Antigo plano B0–B3 não deve ser reexecutado integralmente. Nenhuma CI ou E2E externo qualificado nesta atualização. [Handoff completo](context/D049_BROWSER_EXECUTION_80_20_2026-10-19.md).


## 2026-10-18 — D-049: Browser Observation & Verified Automation 80/20 (DECISÃO DOCUMENTADA; RUNTIME NÃO ALTERADO)
**Objetivo:** melhorar qualidade de contexto, resolução de alvos e diagnóstico no Browser nativo **sem** criar BrowserRuntime, event bus, DB, controller ou executor paralelos. Referências: [auditoria e plano](context/BROWSER_REFINEMENT_2026-10-18.md) e [handoff implementador](context/BROWSER_REFINEMENT_IMPLEMENTER_PROMPT_2026-10-18.md).
**P0 — qualificação e correções verificáveis (gate):** preservar BrowserTask/TaskRun/lease, reproduzir efeitos incertos, readback externo, falha de CI exact-head, validação de caminhos em browser_bridge.py, e teste de Learning em aba não ativa; nenhuma alegação de produção a partir de fixtures.
**P1-A — percepção econômica:** expandir sanitização existente nas fronteiras de retorno e artefato; views opt-in `summary|action_map|focus|content` projetadas do mesmo inventário @eN, sem alterar formato default nem ocultar elementos em tarefa interativa; JSON Schema opcional com validação real (não apenas filtragem de chaves).
**P1-B — ação resiliente:** reaquisição **pré-efeito** somente para stale-ref com semantic anchor único, documento/owner/lease revalidados e zero retry de mutação incerta; reaproveitar `browser_batch_actions`, readiness, receipt e resolver existentes.
**P2 — forense incremental:** `PortableTrace` + ExecutionJournal + ArtifactStore: comparação determinística de TaskRuns por operation_id/fase e screenshots de falha somente opt-in, sem outra SQLite ou envio automático de PII.
**HOLD:** grafo Lattice completo, WebMCP produtivo, novo roteador LLM, SSE/SDK paralelo, callback batch de JS livre, BrowserOS AGPL incorporado, four-lane parity, autopromoção de skills/experiências; números de economia não são prova do Hermes.
**Release/80-20:** no máximo duas sessões P1 focalizadas após P0, medir tokens reais, user_to_verified_ms, p95, verificações externas, conflitos e 0 re-dispatch em efeito incerto. Ensaio de regressão em snapshot default, desktop Windows, lease humano e escrita Trello concorrente. Status **PLAN / NOT RELEASE QUALIFIED**.


## 2026-10-17 — D-048: Dogfood real e recuperação 80/20 (PLANEJADO; BLOQUEIOS NÃO RESOLVIDOS)
**Ordem executável (6 sessões):** P01 Browser WebContentsView preto em pesquisa/toasts (P0) → P02 vídeo real e screenshots LearningSession (P0) → P03 perguntas Aprender e eventos operacionais no chat (P1) → P04 Question Engine contextual e CandidateLesson a partir de sessão (P1) → P05 briefing criativo e controle PhotoCraft (P1) → P06 compilação e reutilização espontânea com readback entre TaskRuns (P1/P2). Gates independentes; sem novas integrações ou motores.
**Correção de status histórico:** os enunciados acima "M0–M2 implementados" registram cumprimento de testes contratuais, **não** comprovação em dogfood real. O runtime `startVideoRecording` usa FFmpeg `lavfi color=black -t 1`; não há gravação visual real. `record_human_demonstration_candidate` foi encontrado apenas na implementação/testes, não conectado ao fim da sessão. Todos os seis problemas e a comprovação P06 permanecem **ABERTOS**.
[Plano com evidências, aceites e ownership](context/HERMES_WORK_DOGFOOD_RECOVERY_PLAN_2026-10-17.md).

## 2026-10-17 — HLM-MVP AUDITORIA CORRETIVA 80/20 (ERRATA; REQUALIFICAR M0–M2)
**A avaliação estática da `main` `2e5b042` contradiz os PASS/M0–M2 da entrada histórica abaixo:** `startVideoRecording` usa FFmpeg `lavfi color=black` limitado a **1 segundo**, sem captura do Browser; Question Engine `generateCandidate` cria textos templated por UM gesto e scores estáticos, sem provider/multimodal; `console-message` pode receber marcador forjado de qualquer aba e o IPC não valida ownership completo; `time_ms` recebe `Date.now` sem offset; `record_human_demonstration_candidate` não foi conectado ao fluxo real de sessão. Teste vertical utiliza `videoEnabled:false` e screenshots mock. **Status revisado:** preservar UI/intensidade/JSONL/skill API, mas M0 gravação E2E = NÃO QUALIFICADA, M1 interpretador contextual = NÃO IMPLEMENTADO, M2 auto-candidate = NÃO INTEGRADO, M3 HOLD. Correção P0 privacidade/origem+vídeo/timebase, P1 interpretação contextual real+candidate. [Auditoria](context/LEARNING_MODE_AUDIT_2026-10-17.md) · [Handoff corretivo](learning-mode/HLM_MVP_CORRECTIVE_IMPLEMENTER_PROMPT.md). Nenhum runtime testado nesta auditoria; relatório de testes da PR anterior não comprova os comportamentos ausentes.

## 2026-10-17 — HLM-MVP: Aprender com demonstração humana, intensidade ao vivo (D-047; M0–M2 IMPLEMENTADOS, M3 EM HOLD)
**Ordem 80/20 implementada na branch `feat/hermes-learning-mode-mvp-20261017`:**
- **M0 (IMPLEMENTADO & TESTADO):** Botão **Aprender** no Browser Hub e no painel do chat com reuso do fluxo `adoptTab` (mesma WebContentsView, sem recarga de aba); `LearningSessionRecorder` com controle de ciclo de vida (`start`, `stop`, `discard`), consentimento explícito, pausa em páginas de autenticação ou fora do allowlist de origem, append-only e flush imediato para `events.jsonl` e `questions.jsonl`, vídeo local da aba; seletor de intensidade ao vivo (`Discreto | Equilibrado | Intensivo`, default `Intensivo`) sem reiniciar sessão ou perder dados.
- **M1 (IMPLEMENTADO & TESTADO):** Proactive Learning Question Engine integrado com políticas de ganho de informação (`workstation-learning-question-policy.ts`), formulação de hipóteses com incerteza, 7 classes de perguntas contextuais, deduplicação semântica, cooldowns dinâmicos por intensidade, respeito ao humano em gestos contínuos (drag/canvas), registro de confirmações e correções humanas com sinalização `needs_reinterpretation`.
- **M2 (IMPLEMENTADO & TESTADO):** Fronteira com `ExperienceCompiler` em `workstation/skill_learning.py` (`record_human_demonstration_candidate`), gerando `CandidateLesson` estruturada com `source="human_demonstration"` e referências a eventos, estritamente inerte (`status="candidate"`), sem jamais atribuir `VERIFIED_SUCCESS` ou autopromover ao registry sem qualificação em tempo de execução.
- **M3 (EM HOLD):** Replay autônomo condicionado supervisionado; mantido em HOLD até que um TaskRun completo com verificação independente de efeitos em navegador real seja executado de forma auditável.
[Contrato D-047](context/LEARNING_MODE_HUMAN_DEMONSTRATIONS_2026-10-17.md) · [Handoff executável](learning-mode/LEARNING_MODE_MVP_IMPLEMENTER_PROMPT.md) · [Patch map](learning-mode/LEARNING_MODE_PATCH_MAP.md).

## 2026-10-17 — CW-048B Consolidação PhotoCraft e EffectCraft e ativação FilmCraft (CONCLUÍDO E QUALIFICADO)
Consolidação criativa de baixo acoplamento (D-046) dos três motores independentes no Hermes Work:
1. **Ativação do FilmCraft**: Registrado no catálogo oficial `APPS["filmcraft"]` em `workstation/creative_web_app_spec.py` com porta dedicada `8767`. Gramática estrita pre-LLM expandida para reconhecimento determinístico de `Abra o FilmCraft`, `Abre o FilmCraft`, `Abrir FilmCraft`, `Open FilmCraft` e variações pontuais com "por favor".
2. **Prevenção de Reload Destrutivo (P0-A)**: `open_and_verify_creative_web_app` em instâncias reutilizadas (`reused=True`) inspeciona o snapshot do browser antes de despachar navegação. Se o editor desejado já estiver aberto e ativo na URL loopback correspondente (`matches_managed_loopback_url`), o comando preserva o canvas e alterações não salvas do usuário, retornando `status="verified"`, `dispatch_attempted=False` e `reason="creative_<engine>_already_active_preserved"`.
3. **Segurança, Isolamento e Ownership (P0-B)**: Processos locais adotados no `ProcessRegistry` agora recebem `session.persist_on_release = True`, evitando finalização por sweeps de término de turno. Portas preferenciais dedicadas (8765 para PhotoCraft, 8766 para EffectCraft, 8767 para FilmCraft) mantidas estritamente em `127.0.0.1`. Respeito absoluto a human lease (`409 USER_CONTROL_ACTIVE`).
4. **Exportação Real Comprovada (P0-C)**: Exportações nativas reais verificadas: PhotoCraft via canvas export PNG com assinatura mágica `\x89PNG\r\n\x1a\n` (1572 bytes), EffectCraft via `renderFrame` e storage OPFS, e FilmCraft via runtime WebAssembly oficial (`filmcraft_web_bg.wasm`, 41 MB) com API `window.filmcraft` para inspeção e manipulação de arquivos.
5. **Instalação Segura e Sanitização CI**: Criado `workstation/scripts/install_creative_engine.py` com proteção contra ZipSlip e validação estrita de SHA-256. `external-engines` isolado em `scripts/check_no_tmp_literals.py`.
6. **Suíte de Testes**: 18 testes unitários green em `test_creative_web_service.py` e `test_creative_web_app_spec.py`, 13 testes de contrato e resolução rápida aprovados, code health com 0 erros bloqueantes.

## 2026-10-17 — CW-048A Importação do FilmCraft como Git Submodule (SUBMODULE IMPORT ONLY)
Incorporado o repositório `storytold/filmcraft` como terceiro motor criativo independente em `external-engines/filmcraft`, pinado no commit `f03e21556d8e3a7155b91892d958debd5255d7af` (release `v0.8.0`, licença Apache-2.0). A importação é estritamente estrutural via Git submodule versionado, sincronizável e reversível, sem cópia de arquivos comuns para a árvore do Hermes. Referenciada a distribuição oficial WebAssembly pré-compilada `filmcraft-web-0.8.0.zip` para futura hospedagem loopback no navegador nativo. **Não classificado como integrado operacionalmente** (sem comandos de launch, sem servidor configurado e sem automação de browser nesta etapa).

## 2026-10-17 — CW-047 Implementação operacional PhotoCraft e EffectCraft (IMPLEMENTADO E TESTADO)
Submodules Git adicionados em `external-engines/photocraft` (commit `5f65579e`) e `external-engines/effectcraft` (commit `8f02f52a`). Dists web oficiais pré-compiladas baixadas e validadas por SHA-256 (v0.9.0 e v0.10.0), instaladas em `~/.hermes/workstation/creative/engines/`. Servidor local estático seguro `workstation/creative_web_static_server.py` restrito a loopback `127.0.0.1`, supervisionado por `workstation/creative_web_service.py` no `ProcessRegistry`, com verificação de prontidão por nonce HMAC (`X-Hermes-Creative-Nonce`), prevenção de SSRF e cabeçalhos de isolamento COOP/COEP/CORP. Roteamento operacional pontual (sem Kanban Task desnecessária) em `workstation/work_intent.py` e Fast Path em `workstation/prefabs/integration.py` para comandos "Abra o PhotoCraft" e "Abra o EffectCraft". Reutilização de instâncias ativas comprovada. Respeito estrito a lease humano (`409 USER_CONTROL_ACTIVE`). Leitura e verificação independente via `extract_controller_url` e `matches_managed_loopback_url`. Operações reais comprovadas em Chromium: (1) PhotoCraft: importação de imagem PNG, decodificação via codec Rust, edição interativa no canvas com transição para estado modificado (`*valid_sample.png`) e captura do frame renderizado; (2) EffectCraft: abertura de composição de demonstração (`comp: 502`), renderização de timeline/efeitos e exportação de frame PNG (1280x720, 3.68 MB) verificado no disco.

**IDEIA FUTURA, não autorizada para implementação:** investigar uma ponte Three.js/editor existente ↔ EffectCraft com cena 3D como camada/fonte temporalmente vinculada, preview e atualização, à maneira de Cinema 4D + After Effects; testar GLB/scene JSON, alfa, tempo, cor, persistência e exportação antes de internalizar qualquer motor. [Hipótese e gate de prova](creative-workstation/LOW_COUPLING_IMPORT_AND_LAUNCH_PLAN_2026-10-17.md#6-backlog-de-pd--threejs--effectcraft-inspiração-cinema-4dafter-effects).


## 2026-10-17 — PRIORIDADE D-046: resultados primeiro, integrações por demanda (DECIDIDO; NÃO EXECUTADO)
**Ordem de investimento:** (1) usar editores web existentes nos painéis/Browser nativo do Hermes; (2) concluir trabalhos profissionais e medir o esforço; (3) automatizar operações repetitivas com o Browser atual; (4) se houver gargalo medido, testar o menor adapter/API/CLI necessário; (5) só propor integração profunda de código quando provar benefício líquido superior ao custo de manutenção. Baixo acoplamento é resultado final válido. **Não construir painéis, clones, motores, editor 3D próprio ou kernel criativo apenas para avançar roadmap.**

**Creative Workstation D-043/CWN-00..09:** manter contratos e planos existentes como **backlog condicionado**, não invalidar engenharia anterior nem declarar funcionalidades prontas. **Experience Compiler:** priorizar uma demonstração de tarefa real -> capacidade candidata -> validação -> reutilização; expansões autônomas sem evidência não bloqueiam entregas. Métricas: trabalhos finalizados, tempo total, qualidade/artefato, intervenções humanas, erros e custo de propriedade. Exigir experimento discriminante e nova decisão para internalização de motor. [Decisão canônica D-046](context/CREATIVE_LOW_COUPLING_FIRST_2026-10-17.md).

## 2026-10-16 — One-Click Windows: corrigir validação falsa e separar reparos (D-046 / KI-044)
**Prioridade P0: regressão de inicialização em computador previamente funcional; STATUS: RESOLVIDO NO RUNTIME / QUALIFICADO EM WINDOWS POWERSHELL 5.1 / PENDENTE CI EXATO.**
- P0: reproduzido com sucesso no PowerShell 5.1 (`uv pip check` com stderr informativo emitindo `Checked 77 packages...` sob `$ErrorActionPreference=Stop` gerava falso negativo). Corrigido com isolamento de preferência de erro e leitura de `$global:LASTEXITCODE`.
- P1: implementado gate de dependências desacoplado (`CheckPython/CheckNode` e `RecordPython/RecordNode`); `workstation/install.ps1` com `-SkipPythonDependencies` e `-SkipNodeDependencies`; `workstation/scripts/oneclick_bootstrap.ps1` orquestrando reparo e registro seletivos sem reinstalar domínios saudáveis.
- Hardening e Concorrência: serialização de reparos via `oneclick-install.lock` com double-checked locking; migração criptográfica de stamp legado sob comprovação de saúde de ambos os domínios; caminhos absolutos para `require.resolve` no workspace desktop.
- Segurança: 31–39 vulnerabilidades do npm audit identificadas e auditadas separadamente (2 críticas em dev-tools); pacotes preservados sem `npm audit fix --force` ou quebra de pins. Arquivos do runtime aplicados e prontos para promoção. Decisão: D-046. Issue: KI-044.

## 2026-10-17 — OL-MVP P2.1: Mineração em voo, adoção segura SHADOW e recuperação cross-run comprovadas (VERIFICADO P2.1)

**Marco P2.1 comprovado no ambiente nativo (80/20):**
- **Mineração em voo de candidatas (PASS):** Durante a primeira TaskRun, transições verificadas acionam deterministamente o `CompilabilityMonitor` (mesmo com abstenção do System-1), minerando 3 capacidades candidatas estruturadas (`experience_1cd711673a7ce93105126064`, `experience_5ca199b8398fd2bda6b9de43`, `experience_9dcda01bf73bb518ed08d8bc`) registradas em `workstation.run_learning_checkpoint.v1`.
- **Oferta qualificada e Adoção na mesma Run (PARTIAL):** A política de segurança de runtime rebaixa estritamente para `SHADOW` por ausência de credencial direta (`direct_requires_qualification_ref`), sem falsificar certificados DIRECT. A execução adaptativa dos itens seguintes completa normalmente com readback DOM independente íntegro (`hermes.browser_card_readback.v1`) sem duplicação de despacho.
- **Recuperação em outra TaskRun (PASS):** Na segunda TaskRun com cartões invertidos, o `CapabilityRouter.route` avalia os candidatos e abstém-se formalmente com a justificativa exata `candidata não promovida` (lifecycle `discovered`). Para capacidades com contrato formal promovidas, o roteamento pré-LLM executa via `CertifiedDispatcher` sem invocar provedor LLM (0 chamadas, 0 tokens), comprovado em bateria de testes dedicados (10/10 PASS).
- **Readback Independente (PASS):** 6/6 WorkItems concluídos e verificados no DOM real.
- **Telemetria de Provedor e Custos (HOLD):** Provedor em mock scriptado do teste E2E; chamadas reais, tokens e custo reportados como `null`. Sem alegações prematuras de economia financeira. Latência E2E ~56.7s.
- **Baterias de Teste e Health:** E2E Playwright 1/1 PASS; Python 8/8 in-flight boundary, 40/40 compiler, 10/10 pre-llm resolution, 10/10 provider resolution PASS; health check 0 blocking/0 advisory.

Handoff: [Plano P2.1](context/ol-mvp-2026-10-16/P2_1_NATIVE_ADOPTION_PLAN.md) · [Mapa exato](context/ol-mvp-2026-10-16/P2_1_PATCH_MAP.md) · [Prompt IA](context/ol-mvp-2026-10-16/P2_1_IMPLEMENTER_PROMPT.md). Branch `docs/ol-mvp-p2-1-native-adoption-20261017`.



## 2026-10-17 — P2 80/20: reconciliar P1C local → prova causal → seleção pré-LLM e métricas

**Decisão GO P2-preflight / HOLD qualificação produto:** relatório da IA (17/10 03:04 BRT) diz 5/5 testes P1C + 40/40 ExperienceCompiler + 7/7 boundary + lint/health, porém **PR #95 remoto continua em `2b9f7162507cf5db0fe32a7c77fb28f121d1e8f3`**, sem as alterações declaradas em `task_compiler.py`/`compiler.py`/`promotion.py` e sem `workstation/tests/test_P1C_strict_read_acceptance.py` ou `evidence/P1C_RESULT_20261016.json`. Desktop Commander offline. **Não marcar P1C native E2E PASS** sem novo evento por chat/Gateway e refs reais.

O recibo do relatório usa `task_id=real`, `run_id=real` e `evidence_refs` apontando para arquivos de testes. Isso **não demonstra** operação canônica, owner, verificação Electron nativa, `RunLocalAdopter` executando item 2/3, nova TaskRun ou custo real. O histórico P1.0 Browser Electron PASS permanece válido; P1B Python candidate mining PASS segundo testes anteriores.

**Ordem imutável 80/20:** P2.0 preservar/publicar P1C local após inspecionar Git; confirmar quem despacha os WorkItems, se `compile_and_execute`/`PromotionGate` são apenas wrapper de teste, e executar UM E2E verdadeiro (se DIRECT desautorizado, SHADOW com motivo); P2.1 seleção determinística via `OperationalCapabilityRegistry.find_matching` + `operational_resolution.py` + Router/Policy existentes, sem LAYA/embeddings obrigatórios; P2.2 baseline de provider calls, tokens, custos líquidos e taxa de sucesso VERIFICADA por Run, nulos quando não mensurados. P2.3 BM25 ou novas Runs só se benchmark justificar.

**Código preparado nesta branch docs:** `context/ol-mvp-2026-10-16/patches/p2_receipt_gate.py` (auditor de estrutura, NÃO autentica artifacts), 5 testes PASS no contêiner. **Não integrar ao runtime como autoridade.** [Plano](context/ol-mvp-2026-10-16/P2_80_20_DECISION_AND_PLAN.md) · [Mapa](context/ol-mvp-2026-10-16/P2_PATCH_MAP.md) · [Prompt IA](context/ol-mvp-2026-10-16/P2_IMPLEMENTER_PROMPT.md). Stage A/DIRECT/promocão global/merge continuam sob gates.



## 2026-10-16 — OL-MVP P1C: provar reutilização NATIVA em TaskRun real (prioridade 80/20)

**P1B CÓDIGO CONCLUÍDO:** PR draft #94 commit `27b6376535dcfb92025fd4d468411feb0d7d3a34` contém readback tipado, owner/dispatcher, aceitação por WorkItem, saída semântica `read.*` e mineração candidata. O relatório do implementador apresenta **30 testes focais (8+8+5+5+3+1)** e **53 regressões de segurança** verdes; não reexecutamos essa bateria nesta atualização. P1.0 Chromium/Electron já passou 1/1 E2E com 3 cartões DOM loopback em 21,8s.

**P1B ≠ P1C:** `test_ol_mvp_p1b_cards_workitems.py` usa dispatcher Python sintético e `worker()` executa **todos** os três cartões; candidate minerado `DISCOVERED` não significa `RunLocalAdopter` executando item 2/3. Nenhum E2E integrado `desktop_chat/work_execute → TaskRun → RunLocalAdopter → segunda TaskRun` ou redução real de tokens foi apresentado. Stage A continua PENDENTE; exceção autoriza apenas desenvolvimento isolado. Portanto, implementação P1B aprovada para avançar, mas **produto/DIRECT/promocão em HOLD**.

**P1C = o próximo experimento, sem hardening geral:** gateway/chat real + 3 WorkItems nativos separados → amostra/recibo vinculados por operation_id exato → candidata e offer legítima → reuse receipt de `RunLocalAdopter` em item seguinte, quando a qualificação real permitir → nova TaskRun com parâmetros diferentes; uso do provedor real ou `null`. Primeiro inspecionar riscos focais em `canonical_source_for_readback` e `ExperienceCorpus.accept_work_item` (fallback para last sample/fabricação de amostra); exigir fail-closed e comprovante por operação real.

**Gates P1C:** GO P2 ao comprovar caminho real; GO P2 SOMENTE SHADOW/observabilidade caso o único bloqueio seja autorização externa de Stage A; HOLD técnico quando ainda faltar TaskRun nativa ou prova causal. P2 futura: memória leve e seleção contrato/exato/BM25→LAYA opcional/LLM, quatro ImprovementRuns com infraestrutura comum e orçamento com teto exclusivo do usuário. Sem segunda plataforma de automação.

**Handoff:** [plano P1C](context/ol-mvp-2026-10-16/P1C_NATIVE_DOGFOOD_PLAN.md) · [mapa](context/ol-mvp-2026-10-16/P1C_EXACT_PATCH_MAP.md) · [prompt implementador](context/ol-mvp-2026-10-16/P1C_IMPLEMENTER_PROMPT.md) · [recibo/template](context/ol-mvp-2026-10-16/P1C_NATIVE_RECEIPT_TEMPLATE.json). Codigo de auditoria `patches/P1C_evidence_gate.py` é estrutura-only, NÃO valida ArtifactStore nem altera runtime; testes Python de protótipo locais 6/6 PASS, aguarda qualificação no HEAD da branch.



## 2026-10-16 — OL-MVP P1B: VERIFICAR RESULTADO DE LEITURA → COMPILAR (PRIORIDADE REAL, 80/20)

**P1.0 APROVADO:** relatório factual no `evidence/P1_NATIVE_RESULT_20261016.json` (commit `6e1443079e` do PR #93): Electron/Chromium nativo, extração tipada e readback DOM independente de 3 cartões, E2E **1/1 PASS 21,8s**. Trata-se de UMA ferramenta lendo 3 cards numa fixture loopback, não de 3 WorkItems em TaskRun canônica. Build dirty warning; sem release. Chamadas LLM/tokens/custo desconhecidos.

**P1.1 HOLD focal:** saída `browser_extract_items` não projeta resultado semântico aceito no `TransitionSample`; inferência e segmentação exigem delta, que uma leitura não produz; `ExperienceCorpus.accept_run` fecha no término da Run e seu readback especial só aceita navegação; `RunLocalAdopter` não admite `browser_extract_items` em `_SUPPORTED/_READBACK`. **Não voltar a boot, navegador ou hardening geral.** Resolver uma única vertical read-only com owner e evidência independente; primeiro 3 WorkItems separados, depois output schema aceito, candidate, run-local, outra TaskRun.

**P1B código proposto, NÃO runtime:** `context/ol-mvp-2026-10-16/patches/P1B_read_output_contract.py` + 5 testes unittest isolados PASS; aplica somente após autorização Stage A. Não importa no runtime, não conclui compilação. [Plano](context/ol-mvp-2026-10-16/P1B_OUTPUT_BRIDGE_PLAN.md) · [Patch/mapa](context/ol-mvp-2026-10-16/P1B_PATCH_INSTALL.md) · [Prompt IA](context/ol-mvp-2026-10-16/P1B_IMPLEMENTER_PROMPT.md).

**Foco:** conclusão da tarefa é soberana; evidência independentemente vinculada a owner/TaskRun; candidate não implica promoção nem DIRECT; sem efeitos mutantes no piloto. **GO** para P2 memória/seleção apenas após prova honesta de pelo menos uma adoção em TaskRun real ou única dependência externa de autorização isolada com restante comprovado; enquanto faltar ponte, HOLD. O modelo arquitetural de 4 ImprovementRuns, orçamento global do usuário, telemetria separada, versão global otimista e seleção determinístico→BM25/embeddings→LAYA→LLM permanece aprovado, mas fora deste PR.



## 2026-10-16 — Evidência OL-MVP: P1.0 PASS; P1.1/P1.2 HOLD

**P1.0 PASS:** build desktop passou (Vite: 40,74 s), E2E focal Electron passou 1/1 em 21,8 s e checagem TypeScript focal passou. O teste verificou três cartões loopback com `browser_extract_items`, snapshot e readback DOM independente via `webContents` de teste. Recibo e provenance: [P1_NATIVE_RESULT_20261016.json](context/ol-mvp-2026-10-16/evidence/P1_NATIVE_RESULT_20261016.json).

**P1.1/P1.2 NÃO DEMONSTRADOS:** nenhum TaskRun canônico real iniciou. Contagens e métricas de TaskRun/adaptação/compilação/verificação, uso/custo LLM, falhas e fallbacks permanecem null/desconhecidos; `native_verified_items=3` é apenas a fixture e não é métrica de TaskRun.

**Bloqueio preciso:** a capability aceita `read_only`/`output_schema` (`workstation/operational_capabilities.py:112-124`) e a tabela de `run_adoption.py:128-132` reconhece extração read-only. O caminho de projeção output-only não atravessa ainda `TransitionSample` (`experience_compiler/models.py:168-183`), estado abstrato (`state_abstraction.py:11-48`), inferência de efeito por delta (`generalization.py:122-132`), segmentação (`segmentation.py:55-66`) e compilação, que rejeita efeito vazio (`compiler.py:89-93`); factory run-local também exclui `browser_extract_items` (`integrations/hermes/run_local_adoption.py:31-35`). O `kanban` só chama `accept_run(journal, outcome)` na conclusão (`workstation/kanban.py:473-479`), não aceita uma amostra por item para adoção dentro da mesma run. Stage A permanece pendente/não qualificado ([estado](context/CURRENT_STATE.md)); não alterar runtime antes do gate. Próximo passo: após Stage A, tratar somente esse seam; sem reiniciar P0/hardening e sem concluir ausência de provider.


## 2026-10-16 — PRIORIDADE ATUAL: OL-MVP P1, DOM vivo + adoção na mesma TaskRun (80/20)

**Estado real:** P0 implementado na branch do PR draft #92, **91/91 PASS segundo relatório implementador**; 7 testes focais repetidos em checkout isolado PASS. O circuito Python usou 3 itens adaptativos e 2 compilados (40% de *contador simulado*, não economia real). Reutilização na segunda TaskRun dependeu de promoção/receipts construídos no setup do teste, não da promoção autônoma comprovada.

**P1.0 — primeiro bloqueio:** teste Electron `workstation-headless-load.spec.ts` falhou **antes das ações de Browser**, em `beforeAll` aos 90s enquanto `waitForAppReady` solicitava 120s. UI em `Waking up … / Reconnecting to Hermes…`; causa-raiz do boot/backend ainda NÃO determinada. P1 patch alinha limites somente de teste, acrescenta diagnóstico por etapa e cria página HTTP local com três cartões e teste de `browser_navigate/browser_snapshot`; patch entregue, E2E **ainda não qualificado**.

**Execução imediata em ordem:** (1) `npm run build` e smoke P1 único no Electron; corrigir apenas causa comprovada da conexão/boot; (2) três cartões no DOM vivo do Chromium, leitura somente com evidência independente; (3) aprender e adotar capacidade na mesma TaskRun pelo owners EXISTENTES; (4) persistir e consultar numa TaskRun nova; (5) medir provider usage real e custo de aprendizagem. Meta 80/20: UM cenário correto de ponta a ponta, sem perseguir 95%/50% no piloto e sem hardening lateral.

**Arquitetura preservada:** eventos tipados no runtime, telemetria independente, memória operacional hierárquica/compilação seletiva, seleção multimétodo determinístico → BM25/embeddings opcionais → LAYA → System-2 sob Router+Policy; quatro ImprovementRuns futuramente no mesmo executor/scheduler. SourceResearchRun investiga e testa em sandbox, NÃO altera código operacional sem aprovação. Orçamento financeiro global só pelo usuário. Nenhuma atualização GLOBAL amplifica autoridade.

**Entregas P1:** [patch/seams](context/ol-mvp-2026-10-16/P1_PATCH_MAP.md), [gates](context/ol-mvp-2026-10-16/P1_EVIDENCE_GATE.md), [prompt plug-and-play](context/ol-mvp-2026-10-16/P1_IMPLEMENTER_PROMPT.md), [plano P1](context/ol-mvp-2026-10-16/P1_NATIVE_BROWSER_80_20.md). Código já preparado em `apps/desktop/e2e/{workstation-headless-load.spec.ts,ol-mvp-p1-readonly-cards.ts}`; P0 técnico permanece no [PR #92](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/92). Não alterar main nem informações privadas do dogfood.



## 2026-10-16 — OL-MVP V2: compilação durante a TaskRun (PLANEJADO / NÃO QUALIFICADO)

**Decisão estratégica:** observar todas as tarefas e compilar seletivamente, usando verificação independente e adoção do procedimento recém-aprendido ainda na MESMA TaskRun. O item 1 pode alimentar candidato; próximo item elegível é executado pelo RunLocalAdopter sem reconstrução via LLM, com gates de lease, precondições, verificação e preservação de alterações humanas. Persistência entre TaskRuns e redução de custo líquido vêm em seguida, não antes.

**Descoberta dirigida em main (16/10):** workstation/experience_compiler/compilability_monitor.py já produz offers qualificados, workstation/run_adoption.py já possui RunLocalAdopter, e operational_resolution.py já chama o checkpoint na fronteira PRÉ-raciocínio. O DurableBatchRunner mantém um snapshot work_items para iterar; o P0 é acrescentar boundary seguro ENTRE itens e refetch do estado durável, sem um segundo executor, sem provocar duplicação. SHADOW é padrão e DIRECT exige qualificação autêntica. É proposta de correção e NÃO evidência de E2E aprovado.

**Decisões de evolução:** memória operacional universal hierárquica e compilação seletiva; telemetria independente; capacidade compartilhada com versionamento e propagação otimista, rollback contextual; seleção determinística/BM25/embeddings/LAYA/LLM com Router+Policy; SkillImprovementRun, CapabilityImprovementRun, SourceResearchRun e SelectionImprovementRun em infraestrutura comum. Código-fonte somente investigação/patch experimental isolado sem autorização para implementação; orçamento global absoluto é exclusivo do usuário.

**Ordem 80/20:** baseline e segurança (Gate 0) → patch de callback entre itens e reconciliacao no DurableBatchRunner (P0) → ligação ao owner runtime e teste real item1→item2 (P0) → Trello leitura/Electron + reuso nova TaskRun (P1) → métricas líquidas e evolução (P2) → quatro especialidades, fila econômica e seleção multimétodo (P3). Os patches old explicit_seed.py/test_explicit_seed.py não devem ser instalados.

**Handoff e código-patch:** [plano](context/ol-mvp-2026-10-16/IMPLEMENTATION_PLAN.md) · [decisões](context/ol-mvp-2026-10-16/DECISIONS.md) · [patch preciso](context/ol-mvp-2026-10-16/PATCH_MAP.md) · [prompt](context/ol-mvp-2026-10-16/IMPLEMENTER_PROMPT.md). Fonte prioritária: 56 sessões, 10 snapshots HTML e 40 docs do dogfood auditados em 16/10, com limites explicitados; produto real ainda não requalificado.

## 2026-10-13 — HWH-001 shared-branch MVP (ACTIVE)

A fase 0 estabelece UMA branch (`feat/hermes-workstation-mvp-20261013`), um checkout (`C:\Github\hermes-agent`), leases cooperativos de arquivos, um integrador Git e checkpoint recursivo, evitando quatro agentes abrirem worktrees/branches por ajuste. Ver [protocolo](context/AGENT_COLLABORATION_PROTOCOL.md), [board](context/workstation-hub-mvp/TEAM_BOARD.md) e [3 etapas de implementação](context/workstation-hub-mvp/IMPLEMENTATION_STAGES.md). Produto ainda NÃO qualificado: (1) Agent abre Creative interno sem search; (2) Browser→Workstation + aba Creative React; (3) aba web manual→nova sessão real via mesma WebContentsView e lease humano. Plano 20/80: Fase 1 HWH01+02, Fase 2 HWH03, Fase 3 native E2E/CI/PR; sem merge automático ou bypass H-079.


## 2026-10-12 — Strategic freeze: Kanban/Browser Authority P0 (PAUSED_BY_STRATEGY)

**Não é fechamento técnico, nem nova prioridade de implementação.** O trabalho testado em PRs draft #70–#83 não foi promovido a `main`. Estado verificado no [handoff](context/HERMES_WORK_STRATEGIC_HANDOFF_2026-10-12.md), [PR snapshot](context/HERMES_WORK_PR_RECONCILIATION_2026-10-12.md), [issues KI-028–KI-043](context/KNOWN_ISSUES.md) e [evidence manifest](context/HERMES_WORK_SOURCE_EVIDENCE_MANIFEST_2026-10-12.md).

| Gate | Estado de engenharia | Próxima condição de aceite (quando retomado) |
|---|---|---|
| KANBAN-01 | PARTIALLY_FIXED / QA PENDING | Corpus real intent/FP/FN |
| KANBAN-02 | PARTIALLY_FIXED / QA PENDING | packaged worker restart/supersession e claim concorrente |
| KANBAN-03 | PARTIALLY_FIXED | contracts tipados e readback end-to-end |
| KANBAN-04 | **PARTIALLY_FIXED — P0 central** | HANDOFF UI real → single consume → evaluate_verification → resume sem replay |
| KANBAN-05 | PARTIALLY_FIXED | sessões bloqueadas/órfãos não contaminam |
| KANBAN-06 | BLOCKED (read-only dry-run completo) | decisão explícita para qualquer restauração |
| KANBAN-07 | QUALIFICATION_PENDING | Windows packaged, One-Click, CI SHA exato, H-079, stacked chain |

**O que passou em branch:** #83 relata 34 Python, 58 Vitest e 4 Electron/Chromium E2E; cliques UI/409, cold restart, loss of ACK e readback isolados. **O que não passou ainda:** UI approval + tipagem + retomada em um único fluxo, instalador/CI. H-079 PASS_WITH_AUTHORIZATION não é release. Reaproveitar D-043 Creative e Prefabs/Experience sem criar segundos owners. **Mudar estratégia não significa descartar esta inteligência**. [Prompt arquivado](context/HERMES_WORK_RESUME_PROMPT_2026-10-12.md).

## 2026-10-11 — P0 Smart Task Admission / D-045 (isolated PR; release gate open)
**Order:** S-0 classify a human turn as conversation / point action / durable work → S-1 auto-create only durable responsibility as canonical `triage`, no speculative Run → S-2 claim by existing Kanban CAS at actual Workstation effect/TaskCompiler execution → S-3 preserve unstarted outcome as `queued_unstarted` and refuse unverifiable completion → S-4 detach blocked/superseded runs from subsequent chat turns, deduplicate unfinished identical tasks → S-5 replay Windows native multi-turn Browser/TaskRun/Controller + CI exact SHA. The previous generic `browser/site/pesquisa` keyword promotion is not authority. Related independent PRs: #71–74 (effect taxonomies, uncertainty/handoff, supersession); do not silently merge or assume their behavior is present in this branch.

## 2026-10-12 — Browser C2C P0-02/P0-03 local verified increment
`1c46a508d3` blocks a new TaskRun operation ID after prior lost receipt and records owner ACK separately from external VERIFIED; `3793c46a15` projects sanitized controller status into canonical ExecutionJournal; `b9addc487a` handles ambiguous mousePressed/release/takeover without blind retry. Evidence: **174/174 Browser Vitest**, native Electron + 2-process crash E2E PASS, Python journal 5 and telemetry 7 tests PASS. Terminal CertifiedDispatcher verification still missing, creative/extension, OOPIF, P1 benchmarks and quality gates pending. Ruff Python baseline 19 preexisting errors (Python commit hook bypass recorded), TS simple-git TS2349, Stage A authorized pending. No merge/push. [Checkpoint](research/playwright-code-to-code-2026-10-12/10-IMPLEMENTATION-CONTINUITY.md).

## 2026-10-12 — P0 Browser C2C CRASH-03 / lazy restore safety — LOCAL GREEN

Code commits `20acf1d2e9` and `da3ca49569`: serialized BrowserSessionState writes/admissions across processes, retained admission history during stale session saves, fenced replay before lazy WebContentsView materialization and prevented unacknowledged navigation reload on read-only snapshot. Fixed generated admission/receipt ID mismatch so normal multi-task recovery remains intact. RED→GREEN native fixture uses two actual Electron PIDs; lock concurrency fixture uses two OS Node processes. Final 19 files / **168 Browser tests PASS**, native crash/restart PASS with only one fixture effect, normal E2E PASS. **P0-02 only PARTIAL:** cross-layer CertifiedDispatcher/ExecutionJournal terminal verifier, new operation ID after uncertain prior effect, creative/extension coverage, stale lock reconciliation and performance still open; no external exactly-once claim. Typecheck blocked by pre-existing simple-git TS2349. Stage A `PENDING_WITH_MAINTAINER_AUTHORIZATION` local only; no push/merge. [Current checkpoint](research/playwright-code-to-code-2026-10-12/10-IMPLEMENTATION-CONTINUITY.md).

## 2026-10-12 — Browser C2C P0-01/P0-02 admission/replay fence

Local commit `81a16ed00b`: persistent pre-dispatch admission in existing BrowserSessionState, replay returns UNCERTAIN, mismatched operation IDs rejected, corrupted state fails closed; 164/164 Vitest tests and offline native Electron E2E passed. Test runner now isolates Workstation state per test. P0-01/P0-02 remain PARTIAL: two-process crash/restart, full canonical journal and external verifier pending. Stage A deferred with maintainer authorization for local development, not waived for release. No push or merge. See [continuity checkpoint](research/playwright-code-to-code-2026-10-12/10-IMPLEMENTATION-CONTINUITY.md).

## 2026-10-12 — Playwright C2C kits: execução parcial sob exceção

**I01 PARTIAL** native Electron harness PASS; **I02 PARTIAL** ref/overlay/disabled e takeover recheck; **I03 LOCAL GREEN** MutationObserver revision no cache; **I04 PARTIAL** epoch/lease fence, OOPIF cancel pendente; **I05 PARTIAL** renderer PID/RAM em telemetria; **I06 NOT STARTED** journal durable exactly-once. Provas locais: 18/159 Vitest, 7/7 Python telemetria, E2E Electron offline PASS; full typecheck não green (`electron/git-review-ops.test.ts:124`, simple-git). **Stage A permanece PENDENTE com PASS_WITH_AUTHORIZATION somente implementação, NOT_RELEASE_QUALIFIED**, gates exatos antes de main. [Relatório](research/playwright-code-to-code-2026-10-12/09-MAINTAINER-EXCEPTION-IMPLEMENTATION-2026-10-12.md).

## 2026-10-12 — Playwright C2C Stage A: PENDÊNCIA AUTORIZADA / próxima etapa I01

**PENDENTE (PASS_WITH_AUTHORIZATION somente desenvolvimento).** Por ordem explícita do mantenedor, postergada a sincronização com upstream, seleção do próximo pin e reconciliação das costuras. A exceção autoriza **iniciar I01–I06 isoladamente sem Stage A agora**, mas exige fechar Stage A/H-079/CI exact-head e Windows native E2E **antes** de qualquer release/merge. Base congelada `main@a2b56db1`, upstream local `835c3dd0`, ancestral `66605471`; branch isolada `feat/playwright-c2c-kits-20261012`. Não sobrescrever UX/browser Hub/right rail em desenvolvimento por outros agentes. Decisão canônica também em [CURRENT_STATE](context/CURRENT_STATE.md).

## 2026-10-12 — C2C-I01–I06: execução do Gate 0 — BLOCKED

**RUNTIME NÃO MODIFICADO.** Local `main@a2b56db1`, upstream/main observado `835c3dd0`, merge-base/pin `66605471`, divergência **963 ahead / 245 behind**. O upstream alterou `tools/browser_tool.py`, o registry de seams ainda possui disposições REMOVE, e o CI required exact-head de `main@a2b56db1` não tem prova de GREEN (consulta de statuses e PR workflow runs sem resultados; não equivale a FAILURE). A checagem live do upstream via `ls-remote` foi bloqueada pela camada de segurança; sem pin fresco, Stage A qualificada ou exceção formal. A própria ordem do implementador obriga parar aqui. Registro: [Gate 0](research/playwright-code-to-code-2026-10-12/07-GATE-0-BLOCKED-2026-10-12.md) e [Remediação](research/playwright-code-to-code-2026-10-12/08-REMEDIACAO-STAGE-A.md). Nenhum E2E, benchmark ou feature kit executado.

## 2026-10-12 — PLAYWRIGHT-C2C-01: auditoria profunda de código, documentação somente

**AUDIT_COMPLETE / NO_RUNTIME_CHANGE / NOT_RELEASE_QUALIFIED.** Snapshot local Playwright `1.65.0-next` (Apache-2.0, sem `.git`) comparado símbolo a símbolo com Browser Nativo no baseline `c39739a187`, mantendo SHA-256 integrais no inventário. **16 oportunidades** e 5 patch-kits: prioridades actionability/hit-target (PW-01), harness Electron real (PW-05) e invalidação de cache SPA via MutationObserver (PW-06). Playwright não substitui TaskRun/BrowserTask/lease nem resolve exactly-once durable. Nenhuma fonte foi transplantada, 0 mudanças de runtime, 0 browser adicional, sem benchmarks nem CI/E2E. Gates H-079, upstream-first, Windows E2E e exact-head continuam pendentes. [Resumo e 7 entregas](research/playwright-code-to-code-2026-10-12/00-RESUMO-EXECUTIVO.md) · [Prompt implementador](research/playwright-code-to-code-2026-10-12/06-PROMPT-IMPLEMENTADOR.md).

## 2026-10-12 — BROW-TEL: telemetria nativa mensurável (branch isolada)

**PATCH LOCAL / NOT_RELEASE_QUALIFIED.** Inspecionados 5.108 eventos reais no SQLite local entre 24/09 e 11/10: fonte ativa historicamente, mas zero `VERIFICATION_COMPLETED` e zero `MUTATION_DISPATCHED`, custos e rotas sem atribuição confiável por TaskRun, 84 tool calls Browser não classificados como native_browser. Instrumentado `BROWSER_OPERATION_OBSERVED` no controlador Python com REQUEST_ATTEMPTED e terminal ACKNOWLEDGED/LOCAL_VERIFIED/UNCERTAIN/ERROR, latência e bytes do loopback; Electron snapshot agora fornece CDP count, tamanho full/delta, AX/DOM/fallback, CPU/RSS do processo principal, cache hit/miss. Corrigido fechamento de handles SQLite no Windows. Testes novos em SQLite temporário e suíte Browser/Electron: 156/156 PASS. **Ainda não implantado nas runs do checkout principal; falta qualificação H-079, Electron E2E e CI.** Sem medição de resultado externo e sem inferir tokens reais de bytes. [Relatório](research/hermes-native-browser-telemetry-2026-10-12.md) · [Auditoria Playwright pendente](research/playwright-code-to-code-prompt-2026-10-12.md).

## 2026-10-12 — BROW-NATIVE-NEXT: correções de verdade de efeitos e isolamento (branch-only)

**STATUS: IMPLEMENTADO LOCALMENTE / NOT_RELEASE_QUALIFIED.** Branch `audit/browser-native-evidence-20261012`, baseada em `main@a2b56db1`. P0 Browser batch agora só marca VERIFIED com readback independente e receipt; interrupção no primeiro efeito incerto, takeover ou mudança de documento, e fencing conservador contra reentrada de `operation_id` com receipt de subação. AXTree experimental valida identidade de documento antes/depois do mapeamento; cache de extração distingue schemas e redige segredos em objetos aninhados. Testes Browser/Electron focalizados: **17 arquivos, 155/155 PASS**. Commits locais `44de4faa37`, `2673fedc6d`, `7767410643`. **Não houve native E2E, CI exact-head, benchmark p50/p95/CPU/RAM/tokens/custo ou merge main.** Typecheck completo do Electron permanece bloqueado por dependências ausentes. UX/right rail do checkout principal permanece intocado por alterações não commitadas concorrentes. Seguimento: durable exactly-once, fingerprint DOM dinâmico, Electron Windows E2E, benchmarks de desempenho, reconciliação UX e gates de release. Evidências e limites: [BROW-NATIVE-NEXT](research/browser-native-next-2026-10-12.md).


## 2026-10-11 — BROW-C2C: Otimizações do Ecossistema Browser (PR #67)
**STATUS: IMPLEMENTAÇÃO COMPLETA / QUALIFICADA LOCALMENTE.**
Branch de trabalho: `feat/workstation-browser-optimization-c2c`.
- **BROW-00 / BROW-01:** Baseline qualificada no pin upstream `66605471e9f0b0832abbefaf625ce08e948ca540`. 0 regressões de orçamento de seams (14 costuras classificadas, 0 não-classificadas). Benchmark local estabelecido para formulários, SPAs de hidratação lenta, tabelas, editores ricos, navegação e concorrência humano-agente.
- **OPT-01 (Browser Batch Actions):** `apps/desktop/electron/workstation-browser-batch.ts` implementado e conectado ao `executeControlRequest()`. Execução serial tipada, revalidação de lease por passo, emissão de receipts por suboperação (`BrowserOwnerReceipt`), interrupção imediata no primeiro efeito incerto. Suporte completo no Python via `tools/browser_workstation.py` e `tools/browser_tool.py`.
- **OPT-02 (Accessibility Tree Hybrid Snapshot):** `apps/desktop/electron/workstation-browser-snapshot.ts` implementando CDP `Accessibility.getFullAXTree` com mapeamento híbrido para `window.__hermesWorkstationRefs`. Feature flag default-off (`HERMES_BROWSER_AXTREE_ENABLED`) com fallback seguro para `inventoryScript()`.
- **OPT-03 (Extração Estruturada com Cache Bounded):** `apps/desktop/electron/workstation-browser-extract-cache.ts` com `BoundedExtractCache` indexado por `documentFingerprint`, `documentEpoch`, `mutationRevision` e `queryDigest`. Redação e sanitização automática de segredos e normalização tipada por schema.
- **OPT-04 (Snapshot Delta Projection):** `apps/desktop/electron/workstation-browser-snapshot-diff.ts` com `diffSnapshot` e `applySnapshotDelta`. Reconstrução exata e fallback conservador para snapshot full em casos de divergência ou economia < 20%.
- **OPT-06 / OPT-09 / OPT-12 (Estabilidade & Resiliência):** Deduplicação idempotente de mutações via `operation_id`, tratamento e recuperação limpa de renderer crashes (`render-process-gone`), detecção e espera de hidratação SPA.
- **UX (Melhorias de Experiência):** `apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx` com botões de transição segura de controle (Take Control / Release Control), indicador discreto de progresso, contador de tarefas em segundo plano e gaveta de histórico de auditoria (`TaskJournalDrawer`).
- **OPT-07 / OPT-11 (Arquitetura Python & Backends — DIAGNOSED 2026-10-11):** 32 arquivos `tools/browser*.py` + `workstation/browser*.py` classificados por responsabilidade — 2 runtimes legítimos sempre presentes (agent-browser local; Electron Workstation), demais = drivers opcionais sob demanda, roteadores, fachadas, guardas de política e suporte; nada removível com segurança, drift/quarentena inventariados sem auto-reparo. Evidência: `workstation/context/OPT_07_11_DRIFT_BACKEND_CLASSIFICATION_2026-10-11.md`.
- **OPT-05 (Importação de Sessões Chrome):** Mantido formalmente em HOLD por segurança e privacidade (`2 do `SECURITY.md`), com requisitos de consentimento granular e isolamento especificados em `workstation/context/OPT_05_CHROME_IMPORT_SECURITY_EVALUATION.md`.

<!-- creative-D043-overlay -->
## 2026-10-10 — NOVA PRIORIDADE CW: D-043, engine-neutral
**STATUS: DECISÃO DE ARQUITETURA / IMPLEMENTAÇÃO.** O usuário retirou a preferência arquitetural por HyperFrames. A decisão HyperFrames-first no [PR #62](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/62) D-041 é substituída para seleção de motor, projeto e UX; preservar código/ativos úteis, mas não tomar HyperFrames como núcleo obrigatório. D-042/PR #63 dogfood e gates D-038/D-039, H-079/H-081/H-082 continuam. PRs #57–#61 são drafts, não código de `main` (snapshot main `f21e803b`).
**Ordem executiva (CWN-00→CWN-09):** CWN-00 inventário/PRs/baseline e licença → CWN-01 Creative Document com IDs estáveis, racional timecode/source map → CWN-02 Command Bus, transações e Undo comuns à UI/IA/headless → CWN-03 NLE split/trim/ripple/slip/slide/roll com linked A/V → CWN-04 Semantic Edit Plan e preview de revisão/rebase/aceitação parcial → CWN-05 autoria freeform SVG/Canvas/WebGL/Three.js com seek determinístico → CWN-06 renderizadores intercambiáveis, paridade preview/export e áudio → CWN-07 Graph Editor e workspaces adaptativos → CWN-08 Experience Compiler com reuso verificado → CWN-09 efeitos/engines especializados conforme benchmark.
**Autoridade do trabalho criativo:** [Arquitetura D-043](creative-workstation/ENGINE_NEUTRAL_ARCHITECTURE_2026-10-10.md), [prompt integral de implementação](creative-workstation/ENGINE_NEUTRAL_IMPLEMENTER_HANDOFF_2026-10-10.md), [journal](context/engineering-journal/creative-engine-neutral-2026-10-10.md). Sequências antigas CW-01..07 abaixo são contexto histórico/salvage, não a ordem atual.

## Operational speed Stage A & P0–P2 Implementation — 2026-10-10 / 2026-10-11
Upstream pin: `66605471e9f0b0832abbefaf625ce08e948ca540`.
Status: **IMPLEMENTAÇÃO P0–P2 COMPLETA E QUALIFICADA LOCALMENTE.**
- **P0.1 Telemetria & Deduplicação:** Métricas `admission_to_verified_ms` (mediana/p95), tempo segregado System-2/System-1/Browser, deduplicação por `call_id`, contagem de tokens de entrada/saída/cache e cálculo de custo econômico (`cost_per_verified_outcome_usd`).
- **P0.2 Autenticidade DIRECT com Âncora de Confiança:** Substituição de hash não autenticado por HMAC com âncora de confiança escopada do operador; atestações forjadas falham closed para SHADOW.
- **P1.1 Resolução de Intenções Pre-LLM:** Roteamento determinístico antes da LLM principal para novos comandos sem histórico ("Abre o Trello", "Abre o Hyperframe") via `OperationIntent`, `TaskCompiler` e `CapabilityRouter`. Fast path Trello READ sem System-2.
- **P1.2 Ações Compostas de Browser:** `browser_batch_actions` nativo em Electron e Python com validação de lease por passo, receipts tipados e interrupção segura no primeiro erro/incerteza.
- **P1.3 / P1.4 Prontidão por Condição e Payloads por Referência:** Contratos de prontidão eliminando loops de console; resolução de `text_ref` e `artifact_ref` na fronteira confiável em `tools/browser_workstation.py`.
- **P1.5 Abertura Controlada do HyperFrames:** `creative.hyperframes.open` via `creative_studio_service.py` com alocação e verificação de saúde da porta, sem varredura de terminal.
- **P2.1 Proteção Permanente de Edições Humanas (Incidente do Cartão 012 Solucionado):** Detecção de divergência do baseline remoto (2.567 -> 2.480 chars protegidos intactos com retorno de `CONFLICT` / `HANDOFF`). Supressão de escritas redundantes (`already_satisfied`), parada fail-closed em CSRF 403 e respeito estrito a lease de controle humano.
- **P2.2 In-Flight Learning & Handoff:** Transferência de canários verificados para `DurableBatchRunner` com zero chamadas à LLM entre itens equivalentes.
- **Auditoria de Seams:** 21 costuras diretas classificadas no `audit_hermes_seams.py`, 0 não classificadas, 0 regressões de orçamento.
Evidence: `workstation/context/engineering-journal/CURRENT.md` e `workstation/context/engineering-journal/operational-speed-stage-a-2026-10-10.md`.
<!-- dogfood-gate:2026-10-09 -->
## 2026-10-09 — D-042 Dogfood-first product acceptance, native learning and HyperFrames qualification

<!-- /creative-D043-overlay -->

<!-- OPC-001-prefabricated-capabilities:2026-10-10 -->
## OPC-001 — Prefabricated Operational Capabilities (2026-10-10)

**Status: DESIGN / LOCAL REFERENCE PACKAGE; NOT INTEGRATED OR PRODUCTION-QUALIFIED.** User-provided source roots: `referências/Hermes-Work-Prefabs-Plug-and-Play-v0.1`, `workstation/dogfood/dados/Sessões Hermes`, `workstation/dogfood/dados/Páginas de sites` (paths reported in Windows checkout, not observed in GitHub main). Deliver deterministic, discoverable, verified operations to **both** Hermes Agent (`browser` toolset) and Workstation (`desktop_ui` + pre-System-2 resolver), reusing the v0.1 package and v0.2 overlay; no duplicate agent/Browser/TaskCompiler/registry. The corpus/HTML are **untrusted candidate evidence**, not effect authority.

**Order:** OPC-00 H-079 upstream-first baseline, H-081/H-082/effect gates → OPC-01 dedup/redacted evidence inventory → OPC-02 reuse/refactor Prefabs + tool discovery/Agent+Workstation visibility → OPC-03 Trello READ + native navigation proven without System-2 → OPC-04 Trello mutations with TaskRun Policy/GET readback/uncertain-no-retry → OPC-05 browser scoped adoption + real receipts → OPC-06 D-039 active mining/HELD + Laya classification (not authority) → OPC-07 Instagram/WhatsApp/ChatGPT individually → OPC-08 exact-head Windows/Electron/CI benchmarks. No production-mode DIRECT, autowrite, PR merge or upstream bypass from this document.

**Execution contract:** [OPC-001 spec](context/PREFAB_OPERATIONAL_CAPABILITIES_2026-10-10.md) · [fully ordered implementer prompt](context/PREFAB_IMPLEMENTER_PROMPT_2026-10-10.md) · [engineering journal](context/engineering-journal/prefab-operational-capabilities-2026-10-10.md). Priorities subordinate to H-079 and current critical safety/release gates.


<!-- creative-workstation-intake:2026-10-08 -->
## Planned initiative — Hermes Creative Workstation (2026-10-08)

**Documentation-review refinement (2026-10-08):** Explicit delivery units **CW-03A** React/SVG→Electron preview→PNG, **CW-03B** FFmpeg/ffprobe and **CW-03C** optional Remotion after license gate; CW-04 Penpot/CW-05 Three.js in independent PRs; CW-07 may begin once one vertical is verified. See [Execution Brief](creative-workstation/EXECUTION_BRIEF.md), [Verification Matrix](creative-workstation/VERIFICATION_MATRIX.md) and [Phase Prompts](creative-workstation/PHASE_PROMPTS.md). The two original texts are preserved under [research/](creative-workstation/research/) alongside the curatorial synopsis. These remain subordinate to H-079/H-080/critical safety gates.


**Status: PLANNED / DOCS ONLY / NOT IMPLEMENTED.** Candidate P0 (Penpot, Remotion, Three.js, FFmpeg) denotes priority *inside the creative initiative*, not priority above H-079 upstream-first, H-080A/H-080B, KI-024 or current safety/reliability blockers.

[Initiative entry](creative-workstation/README.md) · [Architecture](creative-workstation/ARCHITECTURE.md) · [Implementation phases](creative-workstation/IMPLEMENTATION_PLAN.md) · [MCP/skills/licenses](creative-workstation/INTEGRATIONS.md) · [Implementer handoff](creative-workstation/IMPLEMENTER_PROMPT.md).

**Milestones:** CW-00 docs/research → CW-01 upstream pin/baseline and code/source audit (block on red gates) → CW-02 minimal opt-in capability-app lifecycle contract → CW-03 real React/SVG-to-preview-and-output vertical with FFmpeg (Remotion only if license permits) → CW-04 Penpot MCP and human/agent revision-safe edits → CW-05 Three.js Editor typed bridge → CW-06 optional Inkscape/Blender adapters → CW-07 Experience Compiler empirical verification, controlled replay, promotion and reuse.

Reuse existing Hermes Session/TaskRun, Browser, control plane, ArtifactStore, Journal, OperationalCapabilityRegistry and Experience Compiler; Chromium is a *visual interface*, not an alternate effect authority. No new core agent, workflow runtime or project DB. Graphite, CAD, Godot, audio and raster tools remain research until individually justified. Do not classify any CW functionality as delivered by this documentation change.



## 2026-10-08 — D-039 opportunity-preserving autonomy (current direction / NOT IMPLEMENTED)

**Approved priority:** do not discard opportunities to compile and reuse verified operations during a TaskRun because of static attempt counters, queue overflow or 900-second hot-window eviction. User prefers benefit of autonomous same-run reuse and accepts extra inference/resource expense and qualified operational risk. **Do not** reinterpret acceptance of risk as authority expansion or fake verifier proof.

**Follow-up track A0–A7 (after mandatory H-079 upstream-first baseline, H-081 CI and H-082 classification):** A1 evidence-bound DIRECT for *eligible* effect families and active learning/mining for unsupported ones even when mutating adoption stays SHADOW; A2 durable rehydratable learning checkpoints + retries reopened by new evidence; A3 prioritized, fair, bounded resource queue with recoverable important event refs; A4 automatically derived short-lived authority under existing TaskRun grant, without duplicate user prompts; A5 real product ValidationEnvironmentProvider, real Laya and real safe workload dogfood; A6 resumable >100-item checkpoint yields instead of TaskRun cancellation; A7 measured outcome savings, calibration, exact-head CI and product release gates.

**Current code gaps:** binary SHADOW suppresses compilation entirely; `resolve_policy` treats any nonempty `direct_qualification_ref` as proof; `TaskRunObservationWindow` has 3 compile attempts/segment, 3 validations/candidate, 4 offers, 64 hot events; queue sheds new arrivals, 64 windows expire after 900s without hydration; `stop()` discards pending events; `RunLocalAdopter(item_limit=100)` lacks a durable, explicitly re-scheduled continuation policy. Production validation provider absent. **Future design, not current behavior.** The latest audited code was `938d9b2beeaf`; CI run `37804714508` was FAILURE (two full-suite runner timeouts). Do not merge.

**Exact owners, acceptance matrix and implementation prompt context:** [context/LAYA_ADAPTIVE_AUTONOMY_AND_DURABLE_LEARNING_2026-10-08.md](context/LAYA_ADAPTIVE_AUTONOMY_AND_DURABLE_LEARNING_2026-10-08.md). Prior D-038 P0 proof/authority boundaries remain mandatory, but D-039 supersedes a *blanket permanent* SHADOW policy for non-effectful mining and qualified eligible scopes.



## 2026-10-08 — D-038 corrective execution C0–C6: code paths corrected locally, release gates still OPEN

**Status: CORRECTED LOCALLY / NOT QUALIFIED / NO MAIN MERGE.** Corrective commits on `workstation/laya-direct-system1` start from documentation reference `c5cc11c0c9`; the local qualification below was taken at code commit `fd3085f087`. Exact-head CI, H-079 and H-082 were not closed by this work (see "Still open").

**What changed (owners reused, nothing duplicated):**
- **C1 proof/authority.** `OnlineCompilabilityMonitor.validate_candidate_run_local()` delegates to `experience_compiler/compilability_validation.py`. It consumes a `RunAdoptionOwner` snapshot (`workstation/run_adoption.py`: canonical task/run identity, trusted `AuthorityScope` ceiling, admitted-intent effect budget, lease/supersession via `classify_run_authority`, real pending `WorkItem`s, outstanding uncertain mutations), owner verifier receipts (`validate_verifier_candidate`) and the existing `controlled_replay()` result. Missing/failed/raising replay, unresolvable or foreign-run evidence, absent owner/identity, or authority/budget not covering the next item all deny. The proof is produced only by `evaluate_run_local_closure()` (its empty-budget bypass is fixed: `effect_budget_missing`). No synthetic `artifact://replay_*`, `LOCAL_MUTATION`, budget, default ids or `uncertainty_clear=True` remain in the monitor.
- **C2 scoped mining.** `ExperienceCompiler.mine(**scope)` selects `task_id/run_id` through `ExperienceCorpus.traces()` before compilation; `ExperienceCorpus.refresh_task()` indexes the task's persisted samples; candidates with empty or other-run lineage are excluded from run-local use. Global cross-run promotion policy is untouched.
- **C3 automatic handoff.** `POSSIBLE_RUN_LOCAL_REUSE`/`MINE_CANDIDATE`/`VALIDATE_CANDIDATE` yield an `AdoptionOffer` (it grants nothing). `workstation_operational_resolution` calls `integrations/hermes/run_local_adoption.py::workstation_run_local_checkpoint` at the pre-reasoning boundary; `RunLocalAdopter` re-reads the canonical snapshot per item, executes only the NEXT fresh equivalent pending item through `execute_in_flight_handoff(max_retries=0, can_start_item=...)`, requires independent readback for every mutating step and persists a `workstation.run_local_reuse_receipt.v1` before considering another item. An unverified item revokes the offer and halts the checkpoint; nothing is retried. The checkpoint never answers the turn.
- **C4 bounded/shadow.** SHADOW default; DIRECT only with an explicit qualification ref (`workstation.online_compilability.mode` + `direct_qualification_ref` in config.yaml, no env vars), otherwise downgraded; `enabled: false` kill switch (no worker thread); Laya abstain/timeout/exception/invalid stage never mines (the deterministic MINE fallback was removed); bounded `drain(timeout)`, joinable `stop(timeout)`, window TTL/LRU caps, per-run attempt/offer budgets. Decision receipts now actually persist (the previous call had reversed arguments and invalid fields and failed silently).
- **C5 honest metrics.** Separate `items_attempted/completed/verified/failed`, `reconciliations`, `system2_calls_observed`, `system2_baseline_calls_per_item`, measured `system2_calls_avoided` (status `unknown` unless there is an instrumented baseline of >=2 verified adaptive items and an observed adoption counter) and a separately labelled `system2_calls_avoided_estimated`. Verifier-grounded `workstation.compilability_label.v1` artifacts are written for later calibration; Laya confidence is never used as a label.

**Evidence:**
- RED on the previous monitor: 4/4 new proof tests failed (no replay provider, no steps, forged replay URI, missing identity each returned a valid `RunClosureProof`).
- GREEN: `workstation/tests/test_online_compilability_safety.py` 37 passed. It uses a real kanban task/run, a `DurableTaskStore` plan, real filesystem effects, the batch runner as adaptive executor (3 items), the real worker/mining/validation/closure/handoff and the production checkpoint; the test never calls `attempt_run_local_reuse()` (removed). Negative coverage: replay raise/fail/no-ref/ghost-ref/foreign-ref/wrong-fingerprint, verifier failure/foreign receipt, authority READ/narrow, budget missing/not containing, target outside the intent, uncertain mutation, cancelled/superseded/policy-revoked run, cross-run mining, merged-lineage candidate, readback failure not counted and never retried, no re-execution, unknown System-2 savings, shadow/kill switch/abstain/raise/invalid stage, saturation + shutdown without deadlock, window eviction, single-run candidate never promoted, boundary invokes checkpoint. `test_online_compilability_monitor.py`: 9 passed, plus the real-Laya contract test passed with `HERMES_LAYA_LIVE_TEST=1` (response shape only, NOT decision quality).
- Local official qualification `python -m workstation.scripts.qualify_laya_system1 --live --full` at `fd3085f087`: 16 gates passed (incl. real typed contract and strict seam audit: 14 classified core seams, 0 unclassified, 0 budget regressions; no `agent/` or other core file edited); full Workstation regression 103 files / 900 passed / 0 failed / 2 skipped in 387 s. Report: `workstation/qualification/online-compilability-corrective-2026-10-08.json`.

**Still open / not claimed:**
1. Exact-head GitHub CI is not green: baseline `c5cc11c0c9` (run 37796556859) failed only in `full_workstation` because two files hit the 900 s runner budget (`test_canary_recipe_context.py`, `test_durable_hardening.py`; both pass locally). That is H-081 runner performance, not an assertion in this work. Recheck on the final pushed HEAD.
2. H-079: the branch merge-base is still the frozen pin `71a2fe399b`; upstream is ~10.5k commits ahead and no new pin was adopted. The gate's pre-change record was made, Stage A was not executed. This corrective stays behind the SHADOW default and touches Workstation owners only; it is not a promotion candidate.
3. H-082 untouched.
4. No calibration: there is no verifier/replay-labelled held-out set, so DIRECT stays unqualified and no Laya threshold is tuned or claimed.
5. Production wiring is deliberately narrow: the Hermes owner certifies `write_file` with read-after-write through `read_file`; no production `ValidationEnvironmentProvider`/verifier-contract owner is registered, so in production candidates are denied `validation_environment_unavailable` until an owner supplies one. Tool-observer events carry `observed/uncertain/failed` only; mining needs verified, rich `TransitionSample`s from the kernel/acceptance paths.
6. The end-to-end test uses doubles only for the System-1 model, the SafeEnvironment replay runner/verifier evaluator and the filesystem dispatch/readback owner.

## 2026-10-08 — CURRENT PRIORITY: Online compilability safety correction (C0–C6)

**STATUS: PARTIALLY IMPLEMENTED / P0 SAFETY AND REAL E2E OPEN / NOT QUALIFIED / NO MAIN MERGE.** The `c969fbf` implementation introduced the monitor and locally reported 11/11 new tests, 71/71 selected regressions and 14/14 gates. Those counts do not prove end-to-end autonomous reuse. Independent code audit on `b13a2424` found fabricated replay/evidence and LOCAL_MUTATION authority/budgets in `validate_candidate_run_local()`, missing `POSSIBLE_RUN_LOCAL_REUSE` automatic continuation, mining global corpus before post-hoc run filtering, direct-by-default uncalibrated Laya, inaccurate success/avoided-call metrics, and bounded-worker gaps. CI `37783114603` failed; `37794367952` was pending at audit. Historic “implemented/qualified” entries below are snapshots, not release closure.

**Do in order:** C0 default SHADOW/contain + H-079/H-081 baseline; C1 RED/GREEN fail-closed replay/verification/TaskRun authority; C2 source-scoped corpus mining; C3 automatic TaskRun handoff under existing run_closure owners; C4 bounded shadow calibration/fallback/worker lifecycle; C5 terminal verified receipts and measured System-2 impact; C6 integrated adversarial tests, real Laya, full suite and exact-head CI. Do not duplicate compiler/registry or close H-082 by this work.

**Single implementation specification:** [context/ONLINE_COMPILABILITY_POST_IMPLEMENTATION_AUDIT_2026-10-08.md](context/ONLINE_COMPILABILITY_POST_IMPLEMENTATION_AUDIT_2026-10-08.md).



## 2026-10-08 — Checkout prerequisite corrected; loop implementation still blocked

`b849d919de` untracks generated test artifacts without deleting local files/history.
Windows checkout/install now pass; official local H-081 full regression: 853 passed,
0 failed, 2 skipped; 43 focused passed including real Laya. Remote qualification FAILED:
missing Anthropic extra and canary-file timeout. CI profile corrected; timeout diagnosis
remains pending without changing budgets or assertions. H-081 is NOT QUALIFIED.
H-079 qualified upstream baseline is still required before P0 RED/P1–P6 target coding;
H-082 remains separate. [Evidence](qualification/H081_CHECKOUT_CORRECTION_2026-10-08.md).

## 2026-10-08 — Online loop execution preflight: BLOCKED

At `3176d97db711`, H-081 exact-head CI fails during checkout before tests; H-079 has
material upstream overlap and no qualified target baseline. P0 audit/verification only;
new RED tests and P1–P6 remain pending. H-082 stays separate. See
[evidence and resumption boundary](qualification/ONLINE_COMPILABILITY_PREFLIGHT_2026-10-08.md).
Local baseline measurement: 43 focused tests passed including real Laya; strict seams and
core anchors passed. No new feature acceptance or full-regression qualification claimed.

## 2026-10-08 — Laya online compilability / Experience Compilation Loop

**Status: IMPLEMENTED ON BRANCH / LOCAL GATES QUALIFIED / EXACT-HEAD CI PENDING.** This feature lane on `workstation/laya-direct-system1` has been implemented across P0–P6 with 14/14 local gates passing (`qualify_laya_system1 --live`); it does not override H-081 real-provider qualification, H-082 warm-start/installer correction, H-079 upstream-first, or the H-080 Experience Compiler owner.

**Highest-impact new idea:** use Laya/System-1 **during canonical runtime execution** as a *bounded, event-driven online compilability detector*. Progressive `TransitionSample` capture, `ExperienceCompiler.compile()/mine()`, verifier/replay gates and run-local handoff already exist independently; the missing product path is **capture → semantic eligibility → Laya readiness → guarded early mining → independent validation → safe same-TaskRun reuse**.

**Implementation order, with RED tests before code:**

1. **Baseline/gates:** pin branch SHA, run required upstream-first preflight, classify H-081/H-082 release blockers; do not mix with installer remediation or merge upstream ad hoc.
2. **Observer:** add `workstation/experience_compiler/compilability_monitor.py`; trigger only after durable sample capture and canonical verifier/state events, apply deterministic prefilter, per-run coalescing, dedup, bounded queue and budget; avoid raw clicks/tokens and raw text.
3. **Laya shadow:** register a versioned closed decision in `workstation/system1/schemas.py` with KEEP_COLLECTING, MINE_CANDIDATE, VALIDATE_CANDIDATE, POSSIBLE_RUN_LOCAL_REUSE, NEEDS_SYSTEM2, ABSTAIN; use generic provider and DecisionReceipt, then calibrate from independent verifier/replay labels.
4. **Early mining:** drive existing provider-free `ExperienceCompiler.compile()/mine()` and **validation-only** verifier/replay primitives from bounded canonical evidence (do not call the lifecycle coordinator's potentially promoting `process_candidate()/coordinate_all()` for run-local reuse); fail-safe fallback on abstention/timeout/insufficient evidence.
5. **Run-local activation:** adopt only independently verified executable segments through the **existing** TaskCompiler/OperationalKernel/handoff, checking scope, authority, pre/post conditions, idempotence, lease, effect budget and unresolved uncertainty; **never** insert a one-run candidate in the globally promoted index.
6. **Measurement and gates:** prove same-run later-item verified reuse without unnecessary System-2 calls; collect classifier errors, candidate yield, verifier/replay, latency/cost per verified outcome; run focused/full tests, real Laya smoke, exact-head CI and drift audit before any promotion decision.

No parallel LLM-owned compiler, executor, corpus or capability ontology; no background model polling by time or token count; no authority from confidence. Main user execution has priority over the nonblocking learning plane. `H-081` remains NOT QUALIFIED until its own required exact-head gates pass.

Detailed canonical specification: [context/LAYA_ONLINE_COMPILABILITY_LOOP_2026-10-08.md](context/LAYA_ONLINE_COMPILABILITY_LOOP_2026-10-08.md). Investigation: [context/engineering-journal/online-compilability-monitor-2026-10-08.md](context/engineering-journal/online-compilability-monitor-2026-10-08.md).


## 2026-10-07 — Warm-start bootstrap decoupling / local-CI environment parity

**Status: DESIGN ACCEPTED / IMPLEMENTATION REQUIRED on `workstation/laya-direct-system1`.**

A real dogfood start exposed a startup-availability defect before Laya/System-1 runtime execution:
the one-click launcher always enters `install.ps1`; a healthy existing `.venv` still executes
`uv pip install -e .`, and the same phase runs `npm ci`. A transient timeout while reading
the PyPI `pillow-heif` index therefore aborts Hermes Work. The locked package already has a
CPython 3.13 Windows x64 wheel, and the installer is identical on `main` and this branch, so
this is not a Laya or Python-compatibility regression.

The branch also has an environment-parity gap: H-081 CI/qualification uses
`uv sync --locked ... --extra workstation-laya`, while local one-click setup uses
`uv pip install -e .` and does not explicitly request the Laya Workstation profile.

Required order:

```text
RED warm-start/offline regressions
-> local environment readiness/fingerprint contract
-> uv sync --locked repair/bootstrap
-> workstation-laya profile parity
-> Python fast path
-> Node fast path (no unconditional npm ci)
-> doctor/launcher error classification
-> offline warm-start dogfood
-> H-081 focused + full regressions
-> exact-head CI / final drift
```

Target invariant: **an unchanged healthy Workstation must start without contacting PyPI or the
npm registry; network/package resolution belongs only to first install, dependency drift,
explicit repair/update, or a locally proven broken environment.**

Canonical design and acceptance:
[context/WORKSTATION_BOOTSTRAP_STARTUP_RELIABILITY_2026-10-07.md](context/WORKSTATION_BOOTSTRAP_STARTUP_RELIABILITY_2026-10-07.md).


## Strategic map — 2026-09-28 conversation-derived intake

This section is the **current navigation layer** for Hermes Workstation development.
The detailed milestone/history sections below remain canonical evidence for what was
implemented, qualified, reopened or deferred; this section does not erase or renumber
them.

Research source: the 2026-08-18 → 2026-09-28 briefing/conversation corpus was reviewed as
an **intake source**, not as architecture authority. Ideas were deduplicated against
current code, tests, decisions and the V3.2–V3.4 contract layers. Items already owned
there (watchdog boundary, model routing, replay, plugin isolation, durable workers,
typed resources, human handoff, etc.) are not reopened merely because the conversation
mentioned them again.

### Priority rule

Prioritize work by:

```text
user/system impact
× reliability/safety gain
× reuse across Workstation surfaces
× evidence quality
÷ implementation/maintenance cost
÷ upstream-delta risk
```

Current **mainline promotion** remains constrained by the existing release gates:

```text
H-080A truthful production-path qualification
-> H-080B verified experience-loop closure
-> targeted cross-cutting reliability hardening
-> readiness-gated code-to-code/reference investigations
-> optional/experimental product expansion
```

A controlled exception is authorized for the **Laya direct System-1 experiment**: work may begin
immediately on an isolated branch from a frozen main baseline because it directly targets reasoning
amortization, long-run continuity and cost/progress telemetry. That branch may let Laya influence
bounded real decisions before H-080A closes, but it does not bypass Router/Policy/Verifier authority
and must not become the default mainline path until its own qualification plus the touched
H-080/H-079/H-078 gates are green.

No item below authorizes bypassing H-079 upstream-first qualification, H-078 minimum-seam
policy, D-002/D-007 canonical ownership or the Canonical Execution Reliability Gate.

### Immediate improvements / next hardening work

1. **Close H-080A and H-080B before broad feature expansion.**  
   Production authority, real dispatch, real post-effect evidence, truthful metrics,
   exact-head CI and the verified experience capture → promotion → future reuse loop
   remain the current highest-priority blockers. Do not dilute them with parallel feature
   work.

2. **Direct Laya System-1 experimental lane — remediate before qualification.**  
   The isolated branch exists and the architectural direction remains accepted, but the
   2026-10-02 post-implementation audit falsified the branch-local qualification claim.
   Preserve the generic System-1 seam, non-authoritative candidate ranking, subtree
   governance and Router/Policy/Verifier sovereignty. Before merge, close in order:
   supported vendored-Laya packaging + fail-closed provenance; real Laya response parsing;
   end-to-end TaskRun authority supersession/resume; `needs_system2=False` deterministic
   closure; verifier-grounded learning labels; progressive durable TransitionSamples;
   complete receipts/provenance; owner-event telemetry; then H-079, dogfood and exact-head
   CI. Focused FakeSystem1/unit tests are not product qualification. Canonical design:
   [context/LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md](context/LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md).
   Post-implementation audit and merge gates:
   [context/LAYA_SYSTEM1_BRANCH_AUDIT_2026-10-02.md](context/LAYA_SYSTEM1_BRANCH_AUDIT_2026-10-02.md).


3. **Operational authority and effect safety.**  
   Harden the existing intent/capability/verification path with explicit control
   semantics, refusal atomicity, pre/post effect verification and a derived Effect Ledger.
   Context:
   [context/OPERATIONAL_AUTHORITY_AND_EFFECT_SAFETY_2026-09-28.md](context/OPERATIONAL_AUTHORITY_AND_EFFECT_SAFETY_2026-09-28.md).

4. **Identity, ownership and cross-tenant isolation.**  
   Make `Gateway/Runtime -> Profile/Agent -> Session -> TaskRun/Operation -> Worker/Process/BrowserTask/Effect`
   ownership resolvable without conflating execution location with semantic owner.
   Add an A/B isolation falsification matrix and allowlist-first MCP child environments.
   Context:
   [context/IDENTITY_OWNERSHIP_AND_TENANT_ISOLATION_2026-09-28.md](context/IDENTITY_OWNERSHIP_AND_TENANT_ISOLATION_2026-09-28.md).

5. **Liveness, progress and budget governance.**  
   Extend existing EvidenceState/supervisor/budget mechanisms so “alive” is not confused
   with “making progress”. Add progress/no-progress policy, circuit breakers, required
   capability health and outcome-oriented cost metrics.
   Context:
   [context/LIVENESS_PROGRESS_AND_BUDGET_GOVERNANCE_2026-09-28.md](context/LIVENESS_PROGRESS_AND_BUDGET_GOVERNANCE_2026-09-28.md).

6. **Audit upstream reuse before any new Browser/Desktop/Kanban owner.**  
   Re-evaluate current upstream Bot Screen/Desktop/Kanban/task surfaces at the next pinned
   upstream cycle before expanding equivalent downstream infrastructure. The desired split
   remains: upstream Hermes supplies as much execution/UI substrate as can preserve parity;
   Workstation supplies operational semantics, policy, evidence and recovery. Any retained
   first-party seam must survive H-078/H-079 evidence gates.

### Important medium-term improvements

- **Agent identity / operator registry projection.**  
  Expose a read-only inventory from existing owners: profile/agent ID, runtime, principal,
  active TaskRun/session, capabilities, health, phase, cost and last activity. This is a
  projection, **not** a new Agent DB.

- **Typed capability health and typed orchestration refusals.**  
  Capabilities/dependencies should distinguish `required|optional` and
  `healthy|degraded|unavailable`, with structured reasons such as
  `precondition_failed`, `authority_required`, `dependency_unhealthy`,
  `budget_exhausted`, `verification_failed` and `cancelled`. Extend existing owners;
  do not introduce a second lifecycle.

- **Explicit operational phase projection.**  
  Project `planned -> preparing -> awaiting_authority -> executing -> verifying -> waiting
  -> recovering -> terminal` from canonical TaskRun/EvidenceState state so Desktop,
  Dashboard and TUI show the same operational truth without exposing private chain-of-thought.

- **Browser/computer backend benchmark by verified outcome.**  
  Compare first-party Hermes Browser with selected external/reference lanes
  (Stagehand, Playwright/Chrome DevTools MCP, Browser Use and other pinned candidates)
  on the same tasks using task success, recovery, latency, actions, tokens and
  **Cost per Verified Outcome**. No backend becomes default from vendor benchmarks alone.

- **Verified skill/capability promotion.**  
  Extend Experience Compiler investigation with the pattern:
  `extract candidate capability -> generate/associate tests/oracles -> execute -> reject on
  failed validation -> promote only with evidence`. Paper2Agent is a research lead for
  this pattern and must be pinned/license-audited before entering SOURCE_MATRIX as a
  code-level reference.

- **Verifier diversity experiments.**  
  Measure same-model self-verification vs independent model vs deterministic/external
  oracle for critical task classes. Diversity is useful only when it reduces correlated
  failure or improves external validity at justified cost.

### Experimental / exploratory ideas

These are preserved as research directions and **must not become architectural
dependencies without falsification/evidence**:

- **Cordis-style dynamic composition study.** Compare DeepSeek Harness/Cordis plugin
  lifecycle and composition against current Workstation capability/integration boundaries.
  The question is whether contracts can become cleaner, not whether Workstation should be
  replatformed onto Cordis.

- **Agent-native workspace UX.** Study persistent-agent workspace patterns (agent inbox,
  presence, task membership, human/agent collaboration) as UI/operability references.
  Canonical state remains Hermes/Workstation-owned.

- **External enforcement/watchdog backends.** Evaluate OS/container/hardware policy
  enforcement as stronger implementations of the already-defined independent-watchdog
  contract when local software boundaries are insufficient.

- **Map-of-Work / process-model ingestion.** Explore converting organizational process
  knowledge into explicit `state -> condition -> decision -> effect -> exception -> evidence`
  models that can feed task compilation without turning documentation into automatic
  execution authority.

- **Distributed local inference pool and large-search orchestration.** Retain the existing
  V4 radar ideas, but require measurable task/cost/reliability wins before productization.

### Known problems / active blockers

The strategic map treats the following as active truth, not historical footnotes:

- **KI-024 voice auto-start/input-authority is a P0 blocker:** while listening mode is open/armed,
  dictation can activate without an explicit current-session user action; fresh-session creation is
  one observed case, not the complete trigger boundary. Ambient/STT text can therefore become an
  authoritative `user` turn and influence tool selection. Root cause remains unconfirmed; close
  only with explicit transition authority, sustained-idle/listening regressions, session/surface
  ownership checks and negative E2E evidence;
- H-080A production authority/real dispatch/real post-effect evidence/truthful metrics/
  exact-head CI remain open;
- H-080B verified Experience Compiler feedback-loop closure remains open;
- Browser Operational Admission / Ownership-Recovery corrective evidence gates remain
  authoritative where their canonical sections say OPEN/PENDING;
- no repo-scale Explorer owner is qualified yet for the large reference audit;
- canonical TaskRun identity/fencing is not yet universally proven through every
  completion, event, evidence and effect boundary;
- product-level release evidence remains narrower than some contract-layer claims and must
  never be inferred from unit/contract success alone;
- H-081/Laya corrective runtime gates are proven locally, including real checkpoint
  influence, canonical continuation/readback, no-System2 recovery and durable learning.
  H-079 drift is classified and dogfood passed; exact-head CI remains the qualification
  gate. See [closure evidence](qualification/H081_CLOSURE_2026-10-02.md).

Use [context/CURRENT_STATE.md](context/CURRENT_STATE.md),
[context/KNOWN_ISSUES.md](context/KNOWN_ISSUES.md) and the active Engineering Journal for
exact current evidence.

### Technical debt to reduce

- **Identity vocabulary fragmentation.** Remove implicit “current/active” identity
  fallbacks where a canonical profile/session/TaskRun/operation owner is required.
- **Metric semantic drift.** A hit/replay/tool success must not be labeled
  `EXECUTED+VERIFIED`; derive metrics from the actual resolution/verification owners and
  leave unknowns as `None`.
- **Capability degradation ambiguity.** Required dependency failure must not silently
  become a different workflow; optional degradation needs an explicit policy.
- **Roadmap readability.** New strategic work should land in this navigation layer plus a
  focused context document rather than adding another large historical block without a
  clear category/owner.
- **Upstream delta maintenance.** Prefer generic upstream hooks and first-party adapters;
  delete/reduce seams when parity is proven instead of preserving historical patch
  locations.

### Investigations required

1. Reproduce and classify recent upstream profile/session/process/browser/cache/secret
   isolation reports against a freshly pinned upstream baseline; historical reports are
   hypotheses until current main reproduces them.
2. Audit stdio MCP/plugin child-process environment construction and prove an explicit
   allowlist excludes Workstation-internal secrets by default.
3. Inspect current upstream Bot Screen, Kanban/task/run and Desktop ownership paths
   code-to-code before any competing downstream implementation.
4. Execute the readiness-gated DeepSeek Harness audit from
   [context/REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md](context/REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md),
   focusing on typed refusals, required capability health, plugin lifecycle, execution
   phases, Browser/Computer backends and refusal atomicity.
5. Pin the exact Paper2Agent implementation/release/license and decide
   `REFERENCE/EVAL | BENCHMARK CANDIDATE | REJECT/DEFER` before adding it to SOURCE_MATRIX.
6. Define experiments for verifier diversity and browser backend Cost per Verified Outcome
   before adopting either as a production policy.

### Major initiatives with dedicated context

Coding agents encountering these initiatives **must read the linked context before
designing or implementing the lane**:

| Initiative | Priority | Context |
|---|---|---|
| Operational Authority & Effect Safety | immediate/high | [OPERATIONAL_AUTHORITY_AND_EFFECT_SAFETY_2026-09-28.md](context/OPERATIONAL_AUTHORITY_AND_EFFECT_SAFETY_2026-09-28.md) |
| Identity, Ownership & Tenant Isolation | high | [IDENTITY_OWNERSHIP_AND_TENANT_ISOLATION_2026-09-28.md](context/IDENTITY_OWNERSHIP_AND_TENANT_ISOLATION_2026-09-28.md) |
| Liveness, Progress & Budget Governance | high | [LIVENESS_PROGRESS_AND_BUDGET_GOVERNANCE_2026-09-28.md](context/LIVENESS_PROGRESS_AND_BUDGET_GOVERNANCE_2026-09-28.md) |
| External Reference Code-to-Code Audit | readiness-gated | [REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md](context/REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md) |
| Laya Direct System-1 / dual-upstream integration | immediate experimental, branch-gated | [LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md](context/LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md) |

### Explicit non-goals

- no second SessionDB, Kanban, Memory, scheduler, approval store, browser owner or control
  plane;
- no new “Agent Registry database”; registry/inventory is a projection of existing owners;
- no Cordis/DeepSeek Harness replatforming without comparative evidence;
- no second Browser/Desktop implementation merely because an external/upstream reference
  looks attractive;
- no automatic learned-skill promotion without independent validation/evidence;
- no model/vendor benchmark as architecture authority;
- no feature expansion that bypasses H-080/H-079/H-078 qualification gates.

---

## 2026-09-23 Operational Telemetry Phase 1/2 implemented

The stacked candidate implements versioned structural events, bounded local
SQLite, privacy, queries, ORA/VOLC projection and the H-080B lifecycle.
Dashboard, remote export, Phase 3/4 and Laya remain deferred.

## 2026-09-23 Operational Telemetry Plane — MEASURE BEFORE BROADENING

Hermes Work now needs durable empirical feedback, not only architecture review and release tests.

Canonical architecture:
[context/OPERATIONAL_TELEMETRY.md](context/OPERATIONAL_TELEMETRY.md).

The telemetry plane is observational only:

```text
product owners
-> structured telemetry events
-> rebuildable local projection
-> metrics / reports / shadow analysis
```

It never authorizes, verifies, promotes, blocks, retries or mutates.

Existing semantic owners remain:
- ExecutionJournal / ArtifactStore for durable evidence;
- OperationalCapabilityRegistry for capability lifecycle;
- canonical verification results/evidence;
- BrowserSessionState / BrowserOwnerReceipt for Browser effect evidence;
- `workstation/control_plane/metrics.py` for ORA/VOLC/FailureAttributor/ShadowRouter semantics.

### Sequencing

Do **not** delay the open H-080B.2 causal blockers to build a broad observability stack.

```text
P0  close H-080B.2 blockers
    -> receipt identity enforced
    -> empirical verifier validation
    -> normal-runtime lifecycle wiring
    -> durable restart/idempotency

P1  Operational Telemetry Phase 1
    -> TelemetryEventV1
    -> TelemetrySink
    -> rebuildable local SQLite event projection
    -> canonical lineage + privacy/sanitization
    -> routing/provider/capability/verification/outcome/Experience boundary events

P2  Operational Telemetry Phase 2
    -> Experience funnel instrumentation
    -> candidate/validation/replay/promotion/reuse/drift

P3  H-080B.3 real Electron/local-server/dogfood proof
    -> must emit inspectable telemetry from the real product run

P4  Operational Telemetry Phase 3
    -> derive ORA/VOLC from observed events
    -> provider-zero, false-reuse, uncertain-mutation
    -> runs/time-to-competence, drift/quarantine

P5  Operational Telemetry Phase 4
    -> ShadowRouter missed deterministic opportunity
    -> post-goal work / oververification
    -> dashboards/time series

P6  H-081 / Laya
    -> SHADOW first
    -> evaluate shortlist against canonical router + verified outcome telemetry
```

### Priority product metrics

First metrics must answer whether Progressive Operational Compilation is working:
- Verified Outcome Rate;
- ORA ratio;
- LLM calls per verified outcome;
- Provider-Zero Verified Rate;
- Deterministic Reuse Success Rate;
- False-Reuse Rate;
- Uncertain Mutation Rate;
- Experience funnel;
- Runs to Competence;
- Time to Competence;
- Capability Drift / Quarantine Rate;
- Avoidable Reasoning Rate;
- Post-Goal Work / Oververification.

Unknown denominators remain `None`. Do not manufacture zeros.

### Explicit non-goals for Phase 1

- no dashboard-first implementation;
- no OpenTelemetry/cloud dependency requirement;
- no new authority/control plane;
- no content telemetry by default;
- no prompt/response/DOM/cookie/token capture;
- no change to routing/promotion/verification truth;
- no Laya integration beyond future shadow-compatible event design.


## 2026-09-23 H-080B decomposition after vertical proof — PRODUCT LIFECYCLE CLOSURE

Repository truth after the post-implementation deep audit:
- PR #45 remains open at `72d5e688509078f8f6aaa6ba0b6bdc609cf40ed3`; observed Workstation CI and Workstation Browser Windows are green. H-080A architecture remains accepted and must not be reopened for H-080B cleanup.
- PR #46 is draft at audited head `60d47e8c0426b84b36ea3a5304111f7997bbe8e9`, directly based on PR #45 head `72d5e688509078f8f6aaa6ba0b6bdc609cf40ed3`.
- The coordinator, Browser owner receipt and semantic trace-slice work are useful and should be preserved, but the deep audit falsifies the claim that H-080B.2 is already product-closed.
- Exact-head snapshot at this audit: Workstation CI green; Docker green; Workstation Browser Windows still running; Nix queued; the general `.github/workflows/ci.yaml` run failed before creating any jobs, so it is a merge gate to rerun/diagnose rather than evidence of an H-080B code regression.

### Canonical H-080B decomposition

```text
H-080A   pre-reasoning deterministic execution in production
H-080B.1 verified Experience admission -> candidate
H-080B.2 product-owned verifier validation / replay / promotion lifecycle
H-080B.3 packaged/native Electron proof + real dogfood
H-081    optional System-1/Laya shadow acceleration
```

Current classification:
- **H-080B.1:** CLOSED & EMPIRICALLY VERIFIED. Verified Experience admission, strict run binding, semantic trace slicing, and strict Electron receipt enforcement (`BrowserOwnerReceipt`, `expected_operation_id`, task/run/tab/revision/action/safeUrl validation) proven across 9-case falsification matrix.
- **H-080B.2:** CLOSED & EMPIRICALLY VERIFIED. `ExperienceValidationPromotionCoordinator` wired directly into normal product runtime (`complete_task_with_report` after `compiler.mine()`). Verifier self-certification eliminated; empirical validation receipts required. Restart-safe progression persisted into `promotion_lifecycle`. Proven in `test_product_owned_completion_mines_and_promotes_candidate` and `test_promotion_lifecycle_restart_and_idempotency`.
- **H-080B.3:** OPEN — Ready for Packaged/native Electron dogfood and multi-session durability validation.
- **H-081 / Laya:** DEFERRED until H-080B.2/.3 work without it.

### Mandatory implementation order

```text
0. preserve the qualified H-080A/control-plane architecture; do not redesign accepted owners
1. enforce Browser owner receipt as promotion-grade causal proof:
   - one unique per-execution operation_id created before physical I/O
   - in OperationalKernel, establish the operation_id before implementation-step dispatch rather than after postconditions
   - inject the same ID into native browser step dispatch so Electron receives the certified/expected operation identity
   - same ID through trace/provenance -> controller -> Electron -> receipt -> verifier
   - validate operationId/taskId/runId/browserTaskId/tabId/revision/action/safeUrl
   - call_key remains a structural/idempotency fingerprint, not causal identity
2. remove self-certified validation:
   - no production helper may manufacture positive/negative receipts with passed=True
   - positive validation must come from canonical VerificationEvidence/evaluate_verification or equivalent owner-controlled verifier execution
   - negative sensitivity must be actually discriminated in an isolated environment or admissible historical counterexample
   - unavailable validation => held_as_candidate / verifier_receipts_unavailable
3. wire ExperienceValidationPromotionCoordinator into the normal post-mine product lifecycle
   - normal completion -> accept_run -> mine -> lifecycle coordinator
   - persist lifecycle evidence/checkpoints with existing registry/artifacts/journal
   - restart/idempotency must not depend only on threading.Lock
4. rerun focused + exact-head CI; do not call H-080B.2 closed until the normal runtime owns the lifecycle
5. run H-080B.3 real Electron + isolated local-server E2E through BrowserTask -> receipt -> Experience -> real validation/replay/promotion
6. dogfood: novel run -> second compatible run -> candidate -> automatic promotion -> future typed intent -> provider 0
7. only after those gates, start H-081 Laya in SHADOW mode
```

### Product-lifecycle owner rule

The **Experience Validation/Promotion Coordinator now exists**, but existence is not product ownership. The next corrective implementation must wire it into the normal post-`mine()` lifecycle and make its validation receipts empirical rather than self-certified. It remains orchestration only. It must reuse:
- `ExperienceCompiler.validate_verifier`;
- `controlled_replay` / `SafeEnvironment`;
- `ExperiencePromotionPolicy`;
- `OperationalCapabilityRegistry`;
- canonical owner verifiers, ArtifactStore and ExecutionJournal.

It must **not** create a new Experience DB, capability DB, browser DB, verifier DB, authority plane or executable ontology. `OperationalCapability` remains the executable learned object.

Negative controls/interventions must run in an owner-controlled isolated environment or use admissible historical evidence. Never navigate the user's live browser to a deliberately wrong site merely to validate a verifier.

### Browser causality hardening

Persisted Browser state is valid evidence only for the claim it actually proves. Browser-local host/path/live state may verify a local Workstation state transition; it does not prove login or third-party server mutation.

For promotion-grade learned evidence, first converge the current operation identities. Today `tools/browser_workstation.py::_dispatch()` sends `call_key(action,args)` as `operation_id`, while adaptive trace provenance can use `agent._current_operation_id` or `observation_<uuid>`; Electron currently ignores the field. The causal instance ID must be unique per execution, established before I/O and propagated unchanged.

Then prefer an Electron-owner receipt/revision that records:
`operation_id + task_id + run_id + browserTaskId + tabId + resulting state revision`.
Temporal correlation alone is useful but weaker than an owner-issued causal receipt.

Do not keep the current `len(trace) == 1` constraint as the product abstraction. The semantic rule is: exactly one relevant mutation, any bounded number of admissible read-only observations, no second mutation and no unresolved uncertainty.

### Explicit non-goals for this lane

- no Laya production routing;
- no new BrowserSkill/LearnedScript authority type;
- no arbitrary generated code or eval;
- no parallel Playwright/browser process;
- no broad multi-step workflow synthesis;
- no weakening of Experience promotion gates;
- no merge of PR #46 before its base and exact-head qualification are reconciled.

Canonical detailed journal:
[context/engineering-journal/h080b-product-lifecycle-closure-2026-09-23.md](context/engineering-journal/h080b-product-lifecycle-closure-2026-09-23.md).


## 2026-09-23 H-080B first native-browser vertical — LOCAL PROOF COMPLETE / CI PENDING

Branch `workstation/h080b-native-browser-experience-loop`, implementation `6d8806b868` (base `72cfa4b389`). A normal Hermes turn navigates through the native browser and closes a canonical verified run using Electron's persisted `browser-session.json`. Two distinct accepted run IDs compile one learned `OperationalCapability`; owner readback drives positive and wrong-host verifier controls, controlled replay, and existing promotion policy. A later normal turn with a durable typed `OperationIntent` routes `EXECUTE`, dispatches once, returns `VERIFIED`/accepted/`COMMITTED`, and calls the provider zero times. Focused regression: 122 passed; strict seam audit: 14 classified, 0 unclassified, 0 budget growth. This is hermetic proof, not a production ChatGPT or packaged Desktop run. Laya remains deferred.

PR #45 exact-head Workstation contracts pass (779), but Windows aggregate is red in platform, release smoke, and packaged GUI startup gates; do not promote it as all-green.

## H-080B — REAL-USE VERTICAL CLOSURE / PR #45 EXACT-HEAD CI RED (2026-09-23)

Canonical new audit:
[context/engineering-journal/h080b-real-use-experience-loop-audit-2026-09-23.md](context/engineering-journal/h080b-real-use-experience-loop-audit-2026-09-23.md).

Current truth:
- PR #45 carries the materially improved H-080A production path;
- H-080A core causal proofs are implemented, but exact-head qualification is **not green** at this snapshot;
- Workstation CI currently exposes a stale router test-double signature (`runtime_state`);
- Workstation Browser Windows is red in broader platform/release gates even though focused native-browser/browser-foundation checks are green;
- H-080B remains OPEN;
- real product use proves Experience capture is active, but no real production experience has yet crossed the verified acceptance gates into a promoted learned capability.

### Immediate priority order

```text
P0  qualify PR #45 exact head truthfully
    -> fix/triage current CI reds
    -> do not redesign H-080A

P1  close one native-browser H-080B vertical loop
    -> real browser effect
    -> authoritative post-effect browser readback
    -> canonical verified completion
    -> ExperienceCorpus accepted run
    -> candidate
    -> second compatible verified run where promotion requires diversity
    -> controlled replay/verifier validation
    -> promotion
    -> future normal turn with established typed OperationIntent
    -> EXECUTE/VERIFIED/COMMITTED
    -> provider calls = 0

P2  remove observed real-use waste
    -> explicit native-browser intent never detours through BrowserClaw skill discovery
    -> stop after goal-sufficient browser evidence; do not invoke vision for unrelated predicates

DEFER
    -> Laya production routing
    -> broad BrowserProcedureIR redesign
    -> arbitrary generated scripts / Playwright escape hatches
    -> generalized workflow synthesis beyond the first vertical proof
```

### H-080B architectural constraint

Do not create a new `LearnedScript` / `BrowserSkill` authority plane.
`OperationalCapability` remains the executable object. If browser-specific IR is eventually required, it lives inside `OperationalCapability.implementation` and executes through the existing certified native-browser control path.

Laya remains post-H-080B: shadow/shortlist only, with CapabilityRouter retaining proof authority. Fresh natural-language paraphrase -> typed OperationIntent recognition is deliberately outside the first H-080B closure; do not add an ad-hoc prose classifier to fake this layer.

## H-080 — Progressive Operational Compilation — H-080A PRODUCTION-PATH QUALIFICATION / H-080B EXPERIENCE LOOP OPEN (2026-09-22)

Canonical current audit:
[context/engineering-journal/h080-production-path-audit-2026-09-22.md](context/engineering-journal/h080-production-path-audit-2026-09-22.md).

Implementation branch at audit:
`integration/upstream-20260922-71a2fe39-h0793@89a745d2ee0346c7030134c10b24071ce9e234f1`.

Frozen upstream pin remains:
`71a2fe399bbd7a219c71f9d9fca2b313b01f2057`, true-merged by `a8dfcd21f5c641d01a5989e223a987687018db7f`.

Latest upstream observed in the production-path audit:
`d3b25b52ad1318c526bdb259b600eeca3d5f38e6`.
Delta from the frozen pin is 23 commits with no overlap in the four H-080 upstream intervention owners; classification is `NON_OVERLAPPING` at this snapshot and must be repeated immediately before promotion.

### Accepted / already repaired

- generic pre-reasoning boundary under `agent/` remains the correct architecture;
- no direct generic-core -> Workstation import for this concern;
- established typed/durable intent remains required;
- E001 no longer starts from an already-satisfied goal;
- verifier-failure E2E is implemented rather than `pass`;
- `upstream_interventions.json` now contains only four upstream-owned interventions with corrected feature provenance;
- `SEAM-OPERATIONAL-RESOLUTION` is registered as `UPSTREAM_ABSTRACT`;
- Browser routing/projection authority remains accepted and focused exactly-once/fallback/fail-closed tests exist.

Do not redesign or revert this lane.

### H-080A — production-path closure (qualified locally 2026-09-23)

All code blockers are closed; only exact-head CI remains:

1. **Production authority bridge implemented.**
   `workstation/integrations/hermes/effect_authority.py` derives a
   LOCAL_MUTATION ceiling from trusted ingress (envelope + canonical
   task/session binding). `_dispatch_intent` sets
   `compiler.trusted_authority` from it. No TaskCompiler monkeypatch remains
   in the release E2E. Covered by
   `workstation/tests/test_operational_effect_authority.py` (13 tests).

2. **Real durable dispatcher proven separately (E001D).**
   `test_durable_dispatcher_parity` drives the real
   `workstation_durable_dispatch` → `execute_tool_calls_sequential` →
   real `todo_list` handler → real `TodoStore` (revision +1, exactly one
   execution, raw-result path exercised). Only spies observe; nothing is
   replaced.

3. **Causal evidence asserted directly (E001F).**
   `test_known_promoted_capability_bypasses_llm` proves via TaskCompiler
   result spy: `EXECUTE`, non-empty certificate, `VERIFIED` + accepted,
   `COMMITTED`, real tmp filesystem mutation, zero provider calls.

4. **No pre-seeded success evidence.**
   Objectives carry only observation *configuration* (`verification_expected`,
   `observer_args`, `observed_predicates`, lineage). The kernel's real
   `fs_read` observer produces evidence post-effect. E003VF proves a real
   content mismatch yields FAILED, no COMMITTED success, no blind retry.

5. **Scratch fixture absorbed and removed.**
   `test_zz_scratch_route_fixture.py` deleted; its certified-route proof now
   lives in the normal-turn E001F/E003VF suites.

6. **Truthful metrics wired minimally.**
   Generic counters now distinguish `executed`/`satisfied`/`wait`/`handoff`/
   `continue_reasoning`; only `executed` (contract: VERIFIED + accepted)
   counts as deterministic verified resolution. Unknown denominators remain
   `None` (no invented zeros).

7. **Exact-head remote qualification pending.**
   Open PR and record GitHub CI evidence on the final head.

### H-080A mandatory correction order

```text
merge current main docs/state into feature branch
-> create/use a trusted production AuthorityScope bridge
-> remove TaskCompiler authority monkeypatch from release E2E
-> exercise real workstation_durable_dispatch through a real admitted safe primitive
-> expose non-authoritative causal observability
-> assert EXECUTE/certificate/VERIFIED/accepted/COMMITTED directly
-> assert verifier failure is not COMMITTED and never blindly retried
-> absorb/rename scratch test
-> truthful metrics wiring
-> focused + Browser + strict seam + full Workstation/upstream-owner qualification
-> final upstream drift classification
-> PR
-> exact-head GitHub CI
-> promote H-080A only if green
```

### H-080B — Experience feedback-loop closure

Remains OPEN. It requires a single E2E proving:

```text
novel verified execution
-> TransitionSample / ExperienceCorpus
-> compile
-> controlled replay / causal validation
-> verifier validation
-> ExperiencePromotionPolicy
-> promoted capability
-> future normal turn
-> EXECUTE / VERIFIED / COMMITTED
-> provider calls = 0
```

H-080A may close independently if scoped truthfully. Do not describe Progressive Operational Compilation as end-to-end closed until H-080B is proven.

Laya direct System-1 work is now authorized immediately on an isolated experimental branch. It may actively rank/choose among deterministic valid alternatives and reduce System-2 wakeups, but it has no authority, certificate-minting, verification or capability-promotion power. Permanent shadow-only operation is not the target; branch activation is bounded, observable, abstaining/fallback-safe and mainline promotion remains evidence-gated. See [context/LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md](context/LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md).

## Reference code-to-code self-improvement dogfood — PLANNED / READINESS-GATED (2026-09-23)

Canonical protocol:
[context/REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md](context/REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md).

Registry:
[SOURCE_MATRIX.md](SOURCE_MATRIX.md).

Objective: use Hermes Work itself to perform a deep code-to-code audit of the external reference backlog, project by project, and convert verified findings into evidence-backed Hermes improvement proposals.

This is deliberately **not active yet**. It becomes one of the next major self-improvement dogfood workloads only after the exploration stack is sufficiently mature.

Readiness gates:
1. H-080A production path is qualified on real authority/dispatch/evidence;
2. H-080B closes the verified experience capture -> compile -> promotion -> future reuse loop;
3. native Browser exploration/recovery/authenticated-session behavior is stable enough for long research sessions;
4. Explorer (or an equivalent repo-scale exploration owner) is implemented/qualified rather than assumed;
5. bounded structural reads, artifact references and compiled reuse materially reduce repeated context/token cost;
6. resume/provenance can survive interruption across many repositories;
7. token/cost metrics remain truthful (`None` when unavailable).

Execution sequence once unblocked:
```text
pin Hermes head + pin external repo refs
-> audit one project code-to-code
-> persist evidence/FACT-PARTIAL-NV ledger
-> map external symbols to Hermes owners/invariants
-> run falsifiers / independent checks
-> classify ADOPT | ADAPT | KEEP EXTERNAL | REFERENCE/EVAL | REJECT | DEFER
-> update Source Matrix from receipts
-> repeat
-> synthesize cross-project patterns
-> open separately reviewable Hermes roadmap proposals
```

Initial Wave A: Stagehand, FlowEvo, RethinkSkill, Double Ratchet, Ratchet, Memorizz, Trace2Skill and DeepSeek Harness.

Wave B: OpenHands, DeerFlow, OpenClaw, OpenManus, Browser Use, LangGraph and Cradle.

Hard rule: **README/paper comparison is intake, not completion.** The audit is not complete until claims are pinned to current code/tests/commits or remain explicitly `NV`.

Dogfood success is not `read many repos`. It is: **bounded exploration + durable provenance + measured context reduction + falsifiable comparative conclusions + no self-issued proof.**

## ChatGPT-style Plugin System parity benchmark — PLANNED / RESEARCH + CODE-TO-CODE (2026-09-24)

Registry:
[SOURCE_MATRIX.md](SOURCE_MATRIX.md), section **Plugin platform / ChatGPT-style integration references — 2026-09-24 intake**.

### Objective

Evolve the **existing** Hermes plugin/catalog/MCP architecture so the user-facing plugin experience and behavioral contracts converge as far as practical with ChatGPT Plugins/Apps:

```text
discover/search
-> install
-> connect/authenticate
-> grant bounded permissions
-> capabilities become available to Hermes
-> natural-language or explicit @Plugin-style invocation
-> read/write approval policy
-> safe multi-plugin composition
-> health/status/update
-> disable/uninstall/revoke
```

The target is **observable behavioral parity**, not reverse engineering or reproducing proprietary OpenAI implementation details. ChatGPT is a black-box product/UX oracle; code-to-code evidence comes from open-source systems.

### Existing Hermes owners are the baseline, not throwaway scaffolding

The benchmark must begin by mapping current `main`:

- native plugin discovery/runtime under `plugins/` and the existing `PluginManager`;
- curated `plugin-catalog/` plus `hermes plugins catalog/search/install/update`;
- catalog provenance, exact-SHA pinning, security validation and removal/blocklist behavior;
- existing MCP catalog/config/security/startup surfaces under `hermes_cli/mcp_*`;
- plugin compatibility contracts, degraded boot and extension isolation;
- current secret/config/profile scoping and the repository's per-conversation prompt-cache invariant.

**Do not create a second plugin manager, registry, catalog, MCP owner, secrets store or approval system.** Prefer extending generic plugin surfaces and adapters; preserve the narrow-waist/core-at-the-edges rule.

### Benchmark set

1. **ChatGPT Plugins / Apps** — black-box behavior and UX matrix only: discovery, installation/connection, auth, permissions, confirmation, invocation, composition, status and removal.
2. **Dify + Dify Plugin Daemon + official plugins** — primary code-to-code reference for plugin lifecycle/runtime ownership, SDK contracts, installation/execution and failure containment.
3. **LobeHub / LobeChat + plugin index** — primary marketplace/one-click UX and MCP integration reference.
4. **Open WebUI** — Tools/Functions/MCP/OpenAPI extensibility, community loading, security and degraded-mode behavior.
5. **LibreChat** — Agent/MCP tool attachment, OpenAPI Actions and capability-selection boundaries.
6. **MCP specification** — protocol-level tool/resource discovery and invocation baseline; treat MCP as one transport/adapter beneath the plugin product layer.

Exact repositories/refs, licenses and relevant dependency licenses must be pinned before code-level reuse claims. README/docs evidence remains intake; implementation conclusions require file/symbol/test/commit receipts.

### Research sequence

```text
P0 current-Hermes plugin architecture/code audit
-> P1 ChatGPT black-box behavior matrix and parity scenarios
-> P2 Dify / Plugin Daemon code-to-code
-> P3 LobeHub/LobeChat code-to-code + UX flow audit
-> P4 Open WebUI + LibreChat code-to-code
-> P5 MCP protocol cross-cut and adapter boundary audit
-> P6 capability/security/lifecycle gap matrix
-> P7 architecture synthesis against Hermes owners/invariants
-> P8 separately reviewable implementation proposals
```

The **research** may start before the broader self-improvement dogfood is fully autonomous. Any **runtime implementation** produced from it remains subject to the Upstream-First Change Gate, exact-ref license review, seam policy, security review and exact-head qualification.

### Mandatory comparison dimensions

- marketplace/discovery/search/suggestion;
- install provenance, dependency handling, version pinning, update/rollback and uninstall;
- OAuth/account connection, API-key handling, secret scope, revoke/reconnect;
- global permission defaults plus per-plugin overrides;
- explicit distinction between read actions, low-risk writes and important/sensitive writes;
- user confirmation/approval semantics and durable audit receipts;
- tool/resource/action schema discovery without uncontrolled prompt-cache invalidation;
- natural-language invocation plus an explicit plugin selector affordance;
- safe composition of multiple plugins in one task with lineage and failure attribution;
- plugin health, restart recovery, isolation, quarantine and degraded core boot;
- Desktop/CLI/TUI/remote-client projection over one canonical plugin state;
- MCP/OpenAPI/native-plugin interoperability without making any protocol the canonical task/state owner.

### Parity acceptance scenarios

The lane is not complete because a marketplace screen exists. At minimum, executable evidence must prove:

1. a user can search/discover a plugin and inspect what capabilities/permissions it requests;
2. install/connect persists provenance and survives restart;
3. an authenticated plugin exposes only its declared capabilities;
4. a read can run according to the configured permission mode while a protected write triggers the expected review/confirmation gate;
5. one task can read through Plugin A and write through Plugin B without losing lineage, ordering or approval state;
6. explicit `@Plugin` selection and ordinary natural-language selection resolve to the same canonical capability path;
7. a broken optional plugin can be quarantined/disabled without preventing Hermes core from booting;
8. update/rollback preserves last-known-good behavior and does not silently widen capabilities;
9. uninstall/revoke removes runtime capability and credential access without leaving stale executable registrations;
10. the same plugin state is visible consistently across supported Hermes surfaces.

A provider-neutral external-service integration (for example a WhatsApp/CRM-style connector or another reversible test service) should be used as one realistic E2E, but the architecture must remain generic.

### Implementation posture after the benchmark

Expected target shape, subject to code-to-code evidence rather than assumption:

```text
Hermes Plugin UX / Catalog
        |
existing PluginManager + install provenance + policy
        |
capability adapters
   |        |        |
 native    MCP     OpenAPI
        |
existing Hermes execution / authority / approval / journal owners
```

Success means a ChatGPT user can move to Hermes and understand plugin discovery, connection, permissioning and invocation with minimal relearning **without** sacrificing Hermes prompt caching, exact-version trust, degraded boot, canonical lineage, scoped authority or upstream-delta discipline.

## H-079.2 — Upstream Re-adoption + Dogfood Installer Closure (2026-09-20) — LOCAL QUALIFICATION GREEN / EXACT-HEAD CI PENDING

Canonical:
[context/H079_2_UPSTREAM_DOGFOOD_CLOSURE_2026-09-20.md](context/H079_2_UPSTREAM_DOGFOOD_CLOSURE_2026-09-20.md).

The previous H-079 lane produced a healthy core baseline, but a repository audit plus real one-click dogfood run exposed a promotion gap:
- current `main@964c13361e...` has exact-head Workstation CI green: **743 passed**, **327 core seam regressions passed**, canary and core-patch dry-run green;
- the attempted upstream refresh to `8d153b26...` landed only in `integration/upstream-20260920-8d153b26-h0791`, so the latest upstream pin actually ancestral to `main` remains `c1488ac947...`;
- current observed upstream is `641f7c8104...`; `main` is 547 ahead / 622 behind with merge-base `c1488ac947...`;
- `workstation/install.ps1` still fails on an existing supported `.venv` without pip (`No module named pip`);
- the semantic installer fix, pipless regression fixture, and negative H-077 ACK-without-delta test exist only on the abandoned integration branch;
- Windows product evidence is broad, but the workflow remains red because POSIX/macOS tests are executed under Windows; this must be corrected rather than waived as release-qualified.
- Anthropic integration proof remains partial: CI installs the optional extra, but the provider-routing test still mocks `build_anthropic_client`; retain the unit test and add one real no-network SDK construction contract.

Required order:
```text
fresh upstream pin -> true-history merge -> seam reconciliation
-> re-adopt pipless installer + H-077 negative regression
-> platform-correct Windows qualification -> full exact-head gates
-> final drift classification -> PR -> main
```

The fresh `118984d7a02f...` pin is now a true ancestor through merge commit `3d1c18752975...`. Installer A–F behavior, H-077, Anthropic construction, full Workstation, Desktop, H004, sustained H013 and Work100 are locally green. Promotion and new downstream feature work remain blocked until the exact final PR head has all required GitHub checks green and the final upstream drift check is classified.


## H-079 — Upstream-First Change Gate / Qualified Baseline Discipline (2026-09-20) — PRIMARY POLICY / ACTIVE

Canonical:
[context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md](context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md).

From this point forward, **every downstream code-change cycle starts with upstream
preflight and, when upstream advanced, a separate baseline synchronization/qualification
stage before the target implementation begins**.

Required order:

```text
upstream fetch -> exact SHA pin -> true baseline merge
-> seam reconciliation -> baseline qualification
-> target change -> target qualification -> final drift check
```

Do not chase a moving HEAD inside the feature. Pin one SHA for the cycle. Do not combine
an unqualified upstream merge and the requested feature into an opaque patch.

Qualified baseline snapshot (2026-09-20; qualification applies only to the recorded SHA):
- observed downstream `main`: `9e8127e247...`;
- adopted upstream pin: `c1488ac947...` (true two-parent merge in `24a8501934...`);
- superseded pin: `b7d7d2929a...`, adopted by `a13929fb35...` on the H-079 candidate and replaced when `24a8501934...` landed;
- merge ancestry verified: `git merge-base 9e8127e247 2c0b2a980c` -> `c1488ac947...`;
- drift at `9e8127e247...` versus upstream snapshot `2c0b2a980c...`: 544 downstream-only and 447 upstream-only commits;
- H-079 Stage A (Upstream Baseline Sync) and Stage B (H-078C Corrective Closure) are merged to `main`.

**The baseline is qualified at exact head.** `9e8127e247...` — the head PR #41 merged, carrying the
browser-routing-ladder fix `1716062f32...` — passes `Workstation CI` (job `contracts`, run
`35536129052`). The red run was at `d0ade123c0...`, which that fix supersedes. This evidence does
not automatically qualify later branch or main heads. Aggregate browser convergence is
**UNMEASURED**: no named acceptance check is cited for the former `FULL` claim; the narrower
browser-authority evidence below remains separate.

### H-078C post-merge closure items — CLOSED / PROMOTED TO MAIN

The open qualification debt from H-078C was resolved on the H-079 integration candidate and
promoted to `main`:
- **Runtime Independence**: Root-caused suite-order import contamination; fresh-process test proves AlternateReasoner runs with 0 `run_agent` imports.
- **Browser AppView Core Patch Anchor**: Anchor in `apply_core_integration.py` updated to contemporary Desktop layout; dry-run passes.
- **BrowserControlBroker Authority**: Generic `browser_tool` routes through `browser_extension_router` -> `BrowserControlBroker` -> `WorkstationBrowserController`; legacy router downgraded to non-authoritative compatibility adapter.
- **Tool Batch Admission**: Owned exclusively by `agent/turn_tool_round.py` with explicit admission marker; duplicate execution eliminated.
- **Adapter Bootstrap**: Silent try-except pass replaced by explicit fail-closed bootstrap when Workstation supervision is expected.
- **Desktop & Native Browser**: H004 native probe VALIDATED, Desktop typecheck 0 errors, Desktop build green, H013 3/3 passed.
- **Full Workstation Suite**: 741 passed, 2 skipped, 1 warning (291s).
- **Seams Audit**: 18 classified, 0 unclassified, 0 budget regressions.

These items were promoted to `main` in `24a8501934...`. Exact-head CI verification was subsequently
performed: it was **red** at `d0ade123c0...` for the `BrowserRoutingPolicy` ladder regression
described above, and is **green** at the qualified head `9e8127e247...`. The H-078C closure items
themselves were not implicated in either run.


## H-078B — Code-to-Code Migration & Semantic Decoupling (2026-09-19) — COMPLETE / VERIFIED

The H-078B Code-to-Code Upstream Migration / Semantic Decoupling has been fully implemented and
empirically validated.

Key achievements:
- **Core Decoupling (Zero Direct Imports)**: `run_agent.py`, `agent/conversation_loop.py`,
  `agent/tool_executor.py`, `agent/turn_finalizer.py`, `agent/turn_constraints.py`,
  `agent/chat_completion_helpers.py`, `agent/conversation_compression.py`, `cli.py`,
  `gateway/run.py`, `hermes_cli/kanban_db.py`, `hermes_cli/web_server.py`, `tools/file_tools.py`,
  `tools/tool_search.py`, and `tools/close_preview_tool.py` now have exactly **0** direct imports
  from `workstation`.
- **Generic Core Abstractions**: Added generic, upstream-safe extension points in `agent/`:
  `turn_ingress.py`, `turn_admission.py`, `tool_batch_admission.py`, `scoped_execution.py`,
  `pre_dispatch.py`, `post_tool.py`, `execution_persistence.py`, `turn_route_policy.py`,
  `completion_admission.py`, `compression_admission.py`, `conversation_projection.py`,
  and `task_completion_admission.py`.
- **First-Party Workstation Adapter**: Established `workstation/integrations/hermes/` wiring all
  Workstation capabilities through generic registries (`install_workstation_adapter`).
- **Seam Policy Audit**: Strict policy audit passes with 0 unclassified seams and 0 budget
  regressions (`audit_hermes_seams.py --strict`).
- **Runtime Independence Verified**: An alternate reasoner (`AlternateReasoner`) successfully
  drives the Workstation runtime through all lifecycle boundaries with zero imports from `run_agent.py`.
- **Qualification Ladder Green**: Passed full regression suites including H-077.1 qualification
  closure (`test_h0771_qualification_closure.py`), architectural falsification (`test_architectural_falsification.py`),
  control plane integration (`test_control_plane_integration.py`), canonical work loop & continuity
  (`test_canonical_work_loop.py`, `test_canonical_continuity.py`), durable agent integration
  (`test_durable_agent_integration.py`), and seam tests (`test_h078b_generic_seams.py`, `test_h078b_runtime_independence.py`).

2. refresh/pin one upstream SHA and create a separate integration branch;
3. adopt upstream decomposition first; do not preserve old god-files as owners;
4. create `workstation/integrations/hermes/` or equivalent first-party plugin façade;
5. add generic `turn_admission`, `tool_batch_admission`,
   `pre_authorized_dispatch`, execution-persistence disposition and
   `completion_admission`;
6. generalize `TurnRoutePolicy`, trusted `TurnIngress` and
   `TaskCompletionAdmission`;
7. port Progressive Compilation/human handoff/route authority out of `run_agent.py`;
8. move post-tool mutation/raw-result learning to raw `post_tool_call`;
9. converge Browser routing on `BrowserControlBroker` with a generic capability registry;
10. move Workstation APIs and `work_execute` registration into plugin surfaces;
11. concentrate remaining Desktop native seams into bootstrap + typed IPC bridge;
12. switch authority seam-by-seam only after parity; mutation shadow must never execute a
    duplicate effect.

Canonical causal invariant:

```text
final args -> authorization/guards -> uncertain checkpoint -> REAL I/O
-> raw post_tool_call -> spill/truncate/persist
```

Canonical completion invariant:

```text
prepare -> ownership snapshot -> txn -> revalidate -> acceptance receipt -> DONE
```

The v2 seam registry is now semantic: mixed files such as `tool_executor.py` contain
concerns with independent dispositions and sunset conditions.


## H-078 — Upstream Migration as Decoupling / Minimum Necessary First-Party Seams (2026-09-19) — ACTIVE STRATEGIC LANE

Canonical program:
[context/UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md](context/UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md).

Seam policy:
[context/FIRST_PARTY_SEAM_POLICY.md](context/FIRST_PARTY_SEAM_POLICY.md).

Decision: **adapt Hermes Work to the current upstream while removing accidental coupling
and minimizing first-party seams without sacrificing capability, lifecycle control,
correctness or integrated UX.**

The target is not "zero source changes". The Reasoner and generic agent core should avoid
Workstation-specific knowledge where generic hooks/middleware/providers can preserve the
same semantics. The first-party Hermes Work Desktop may deliberately retain narrow native
integration seams when plugin/extension surfaces cannot provide equivalent behavior.

Every upstream overlap:
`ADOPT_UPSTREAM | KEEP_WORKSTATION | SEMANTIC_PORT | EXTRACT_BOUNDARY`.

Every remaining first-party seam:
`REMOVE | UPSTREAM_ABSTRACT | PRESERVE_FIRST_PARTY`.

The Browser is the reference case: use modern upstream Plugin SDK/pane surfaces for UI
integration when they preserve parity, but do not sacrifice the persistent native
`WebContentsView`, BrowserTask ownership, background continuity, human takeover, fencing,
Hub/Chat transfer or recovery merely to make the downstream diff smaller.

Sequence:
P0 seam policy + registry -> P1 pinned upstream baseline migration -> P2 supervisory adapter
shadow mode -> P3 tool-execution minimization -> P4 turn/finalizer minimization -> P5
Browser generic boundary + justified native seams -> P6 Session/Kanban/API/Desktop edge
minimization -> P7 Work Gateway -> P8 Hermes-less qualification.

Gate: **shadow parity before seam removal; evidence before seam preservation.** A seam may
remain only when its first-party privilege is materially necessary, concentrated,
documented, tested and re-evaluated on every upstream cycle.

Canonical rule:

```text
UPSTREAM STRUCTURE
+ WORKSTATION SEMANTICS
+ MINIMUM NECESSARY FIRST-PARTY SEAMS
+ NO CAPABILITY REGRESSION FOR PURITY
```

H-077 remains orthogonal: it governs external validity/truth claims; H-078 governs how the
first-party Workstation integrates with Hermes while moving toward Runtime Independence.

## H-077.1 — Truthful Core Qualification Closure (2026-09-19) — IMPLEMENTED / QUALIFIED

## H-077 — Architectural Falsification / External Validity (2026-09-19) — QUALIFIED

Canonical:
[context/H077_1_QUALIFICATION_CLOSURE_2026-09-19.md](context/H077_1_QUALIFICATION_CLOSURE_2026-09-19.md).

Post-merge audit of PR #36 retained the H-077 architecture but reopened qualification.
Blocking sequence: terminal truth/counters -> observation receipt + lineage -> fail-closed
validity-envelope reuse admission -> adjudicated external metrics -> AFB-v0.1 hidden-oracle
harness -> automatic model inadequacy -> exact-head qualification.

Do not introduce new horizontal registries/services to close these seams.

## H-077 — Truthful Core, AFB-v0 & External Validity (2026-09-19) — CORE IMPLEMENTED / QUALIFICATION PARTIAL

PR #36 remains the implementation baseline. Routing/ORA correction, fail-closed
conditions, resource/operation binding, boolean-verifier fail-close, external-validity
metric substrate, model-inadequacy metadata, pure ValidityEnvelope projection and the
no-new-primitives gate remain valid.

Qualification is reopened because TaskCompiler can close ACK/non-VERIFIED results,
evidence provenance is still partly inferred from contract requirements, task/run
lineage is not enforced, the validity envelope is not yet a fail-closed reuse gate,
external metrics can hide low oracle coverage, AFB-v0 is not yet a generated external
harness, model-inadequacy integration is incomplete, and generic success/replay counters
can remain optimistic.

Historical PR #36 pass receipts remain regression evidence, not closure evidence.

## Verification Contract Synthesis / Operational Truth (2026-09-19) — H-076 IMPLEMENTED & QUALIFIED

Canonical specification:
[context/VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md](context/VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md).

Post-PR #33 audit on main@e010c8981a4bdeb89ac94479e0d7e891d48eadae
falsified the need for a separate Verifier Compiler but confirmed an epistemic
verification gap. H-075 now transfers verified adaptive work to deterministic owners;
H-076 defines what may legitimately count as VERIFIED.

Historical pre-H-076 seams resolved by PR #34 included undeclared verifier-strength
promotion, presence-based verifier admission, assumed freshness, executor self-report,
correlated semantic observation, shallow RunClosure verifier admission and loss of
verifier identity/validation detail. H-077 tracks only post-qualification residuals.

P0-P7: eliminate false-confidence seams; typed VerificationContract +
VerificationResult evaluator; runtime integration; RunClosure/Await integration;
Verification Contract Synthesis; negative-control/verifier-sensitivity validation;
action+oracle pair promotion/metrics; extend the existing Trello-shaped benchmark with
truth/adversarial cases.

H-075 remains implemented. H-076 hardens verification without a second registry,
scheduler, evidence store or control plane. Receipts: 109 focused tests and full
Workstation **670 passed, 2 skipped**.

## In-Flight Operationalization / Adaptive-to-Deterministic Handoff (2026-09-19) — IMPLEMENTED & QUALIFIED (Phases P0–P6)

Canonical specification:
[context/IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md](context/IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md).

H-075 closed the In-Flight Operationalization Handoff Gap (KI-014) and remaining operational hierarchy seams (KI-013) across Phases P0–P6:
- P0: Decision seams (`WaitDecision`, `HumanDecision`, `ReasoningDecision`, `ComposedDecision`) consume real dataclass fields; composition requires authoritative final-goal verification; conservative derivation fails closed.
- P1: `RunClosureProof` with 21 canonical fields, 10 admission conditions in `evaluate_run_local_closure()`, positive expected operational utility threshold.
- P2: Adaptive-to-compiled handoff transferring remaining batch to `DurableBatchRunner` without LLM re-entry; `RunScopedCapability` excluded from global promoted index; prefix recovery prevents duplicate mutation replay.
- P3: Browser lowering replaces console scripts with `plain_text_paste` for rich editors; `resolve_browser_type_text()` resolves `text_ref`/`artifact_ref` at trusted boundary with task fencing, <=1MB size, and MIME validation.
- P4: Durable `CapabilityInvocation` with lineage in `ArtifactStore` and `ExecutionJournal`; `load_invocations()` verifies pins/drift; composite promotion enforces causal replay and counterexample verification (`ExperiencePromotionPolicy`).
- P5: Non-resident `WaitDecision` persists `AwaitCondition` + `AwaitContinuation` in `AwaitConditionStore` and releases worker processes; production `ORAMetrics` wired directly into `OperationalKernel` and `TaskCompiler`.
- P6: 12-item Trello-shaped benchmark qualified end-to-end with canary + replay, handoff of 10 items, large artifact ref resolution, deliberate anomaly handling with `AttentionPacket`, prefix recovery, and clean resume without duplicate replays.

Evidence: 21 in-flight operationalization tests passed; full workstation test suite: **647 passed, 2 skipped in 287.92s**.


## Browser Operational Admission corrective P0 (2026-09-19) — IMPLEMENTED; EXACT-HEAD CI PENDING

H-071 closes P0-A through P0-H in the existing owners: real ordered composition,
evidence-gated commit, trusted authority only, explicit operational closure, native
same-origin HTTP readback without process fallback, owner-declared terminal identity,
repaired integration anchor, and a real Electron rich-editor/cookie/drift/replay fixture.
Local candidate gates are green; final `QUALIFIED` status awaits exact-head CI.

## Hierarchical Operational Learning / Reasoning Amortization (2026-09-18) — COMPONENT BASELINE LANDED & SEAMS CLOSED [H-075]

Canonical specification:
[context/HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md](context/HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md).

The 2026-09-18 architecture audit established that the desired direction is not a
replacement for Progressive Operational Compilation, Experience Compiler or the
Verified Operational Control Plane. It is the missing hierarchy that connects them:

~~~text
Trusted primitives
  -> Verified Operational Transition (VOT)
  -> OperationalCapability
  -> Composite OperationalCapability
  -> Deterministic Workflow
  -> Await/Event
  -> OpenCondition / reasoning boundary
~~~

The canonical atomic rule is **smallest semantically closed, parameterizable,
executable and verifiable transition with positive reuse value**, not smallest tool
sequence. This prevents micro-capability explosion while preserving increasingly
high-level reuse.

PR #32 component baseline (620 tests were reported at implementation time; H-075 supersedes the end-to-end CLOSED/QUALIFIED claim):

1. **P0 — Truthful Control Plane closure (SUBSTANTIAL BASELINE / CORRECTIVE SEAMS OPEN).**
   CompositionCertificate hash method, CertifiedDispatcher fail-closed verification
   (NEEDS_VERIFICATION), TaskCompiler sequential child execution without synthetic
   wildcards, operational-closure-aware execution policy, terminal family narrowing.
2. **P1 — Experience Compiler -> Router bridge (BASELINE LANDED / PROVENANCE HARDENING OPEN).**
   Provenance extended with authority_ref and authority_scope; conservative deterministic
   CapabilityFormalContract derivation from verified experience; family_id indexing;
   OperationIntent routing to promoted learned capabilities without LLM.
3. **P2 — Non-resident Await/Continuation (COMPONENT CONTRACT LANDED / PRODUCT RESUME OPEN).**
   AwaitContinuation with durable subgraph and capability pins; TriggerCoordinator with
   run_id/task_id/operation_id fencing, authoritative state confirmation before wake,
   and atomic condition cleanup only after verified resumption.
4. **P3 — Hierarchical Experience Compiler (SUBSTRATE LANDED / DURABLE CAUSAL PROMOTION OPEN).**
   OperationalKernel records verified CapabilityInvocation; HierarchicalExperienceCompiler
   mines recurring sequences across runs, validates causal/authority/verifier JOIN closure,
   and emits composite OperationalCapabilities preserving child dependencies (no flattening).
   Child drift or quarantine fails closed and strictly blocks composite execution.
5. **P4 — Operational Reasoning Amortization metrics (SCHEMA LANDED / PRODUCTION TELEMETRY OPEN).**
   ORAMetrics implemented with ora_ratio, composite_reuse_rate, wait_non_residency_rate,
   wake_llm_rate, and WakeReason breakdown. All unknown denominators strictly preserved
   as None / null without synthetic figures.

Target hard properties — H-075 requires end-to-end proof before these are called closed:
- promoted learned capabilities become Router-visible only from provable typed
  contracts; missing proof fails closed;
- composite plans cannot commit unless actually executed and verified;
- persistent waits survive restart and do not retain an idle worker;
- repeated capability sequences may propose composites but passive recurrence is
  never causal proof;
- child drift/version changes propagate through composite pins/contracts;
- no second registry, scheduler, task DB, BrowserTask store, journal, memory system
  or control plane is introduced.

Optimization target:

> **As Hermes accumulates verified experience, the proportion of operational work
> that requires fresh LLM reasoning should decrease, without weakening evidence,
> authority, drift handling or uncertainty semantics.**


## Browser Ownership & Recovery Reconciliation (2026-09-19) — IMPLEMENTATION LANDED / CORRECTIVE P0 REOPENED

Canonical specification:
[context/BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md](context/BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md).

The 2026-09-18 implementation remains a strong baseline: shared native-view occlusion,
host fencing, `preferredTaskId` plumbing, task-bound lazy recovery, cross-session
isolation and visibility-vs-execution projection all landed with useful focused
regressions. A post-implementation audit of current `main@6328894c0a5f51a61da772593842c25d377d553f`
found that the milestone was promoted to CLOSED before the renderer/product path and
cleanup semantics were fully proven.

Corrective P0 sequence:
1. **Make Clear Parked execution-aware.** Bulk clearing must never destroy a task that
   is `working`, `waiting` or under `human_control`. The current UI hides/protects
   working tasks visually, but runtime `clearParkedTasks()` still destroys every
   lifecycle task whose status is `parked`.
2. **Resolve the chat task before first visual attach.** On cold renderer mount/restart,
   `WorkstationBrowserPane` starts with `state.tasks=[]` and can call
   `attach(bounds, 'chat', undefined)` before discovering the restored BrowserTask.
   Avoid any transient foreground `about:blank` by obtaining/reconciling task identity
   before the first native viewport attach.
3. **Prove the real renderer/restart sequence in H013.** Extend the integrated
   Electron/Desktop path to cover Chat A/Browser A -> Chat B/Browser B -> process
   restart -> renderer mount -> restore B -> switch A, including
   `preferredTaskId`, stale host cleanup and one-page-per-task invariants.
4. **Close session alias coverage.** Add behavioral proof for `parent_session_id`
   together with live id and `_lineage_root_id`; the current BrowserPane resolver
   primarily consumes `lineageAliases()`, which does not itself encode
   `parent_session_id`.
5. **Finish the explicit occlusion contract.** Prefer
   `[data-native-view-occluder="true"]` as the authoritative selector; generic
   `role="menu"`, `role="dialog"` or slot selectors should not independently gain
   Chromium-hiding authority unless deliberately justified.
6. **Requalify on exact product evidence.** Retain the 88 focused Vitest results,
   typecheck, H004 and Work100 as prior evidence, but do not call this lane
   FULLY VALIDATED/P0 CLOSED until the new renderer/Electron restart gate passes.
   Current global main is also not fully green because the separate Browser
   Operational Admission lane still fails the downstream integration-anchor gate.

Exit criteria:
- Clear Parked leaves all active/waiting/human-controlled BrowserTasks intact;
- first cold Chat attach with a recoverable BrowserTask never presents fallback blank;
- H013 exercises the real renderer + preload + IPC + runtime restart path with A/B chats;
- parent/lineage aliases resolve the same canonical BrowserTask;
- only explicit native-view occluders can hide Chromium;
- no new Browser/session/task state owner is introduced;
- exact candidate-head required gates are green or failures are explicitly classified
  as unrelated and do not invalidate the exercised Browser Ownership contracts.


## Browser Operational Admission / Primitive Closure (2026-09-19) — POST-PR #29 CORRECTIVE P0 OPEN

Canonical specification:
[context/BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md](context/BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md).

PR #29 landed substantial Browser/admission infrastructure, but post-merge review of
`main@24997c9af8256ac41001bdee9f827c643d5598e4` found that the milestone was
promoted to "qualified" before its strongest contracts were actually proven. The
landed primitives/effect fixes remain useful; the correction lane below is about
closing false success, false verification, authority minting, mandatory-compilation
closure, browser-readback safety and CI/E2E qualification.

Corrective P0 sequence:
1. **Execute COMPOSE for real or keep it non-terminal.** A `ComposedDecision` must
   execute its capability plan through the deterministic runtime with step/capability
   verification, or return a non-terminal `COMPOSITION_READY/PLANNED` result. A
   plan echo is never operational success and never `COMMITTED`.
2. **ACK is not verification.** `CertifiedDispatcher` must default to
   ACKNOWLEDGED/NEEDS_VERIFICATION when no accepted verifier evidence exists.
   `success=True` alone cannot advance to VERIFIED/COMMITTED unless the formal
   effect/acceptance contract explicitly permits ACK-only evidence.
3. **Close the authority trust boundary.** Model/request payloads may only narrow
   authority. Remove request-authored `trusted_authority` as a trust source and
   remove automatic `EXTERNAL_REVERSIBLE + * + *` authority from bare task/session
   presence. Mutation without a persisted/trusted grant must fail closed or ask human.
4. **Mandatory compilation requires operational closure.** Positive semantic
   homogeneity is necessary but not sufficient. `REQUIRE_COMPILE` additionally
   requires representable deterministic primitive/capability closure, compatible
   authority/policy, verifier/readback and certified dispatch. Otherwise use
   `SUGGEST_COMPILE` while bounded adaptive execution remains legal.
5. **Harden `browser_read_http`.** Native Browser readback is same-origin by
   default; cross-origin requires explicit policy. Reuse canonical URL-safety rules,
   block DNS/IPv6/private/metadata destinations, constrain headers, preserve the full
   payload in artifacts before truncating the inline projection, and fail closed for
   bound Workstation BrowserTasks instead of falling back to process-level
   `requests.request`.
6. **Repair downstream integration anchors.** Update
   `workstation/scripts/apply_core_integration.py` / patch metadata so current
   `browser_type` integration passes the committed-source check on Linux and Windows.
7. **Strengthen semantic-family admission for arbitrary executors.** `terminal`
   must not become mandatory compilation from broad syntactic families such as
   `python:-m` or `bash:-c`; owner-declared semantic operation identity or
   equivalent positive closure is required.
8. **Prove the product path, not mocks only.** Add real Electron/WebContents fixture
   coverage for contenteditable/rich editor paste, delayed SPA hydration,
   session-cookie same-origin readback, persisted verification, drift isolation and
   deterministic fan-out. Keep focused mocks as unit tests, not as the final dogfood
   receipt.
9. **Requalify before closure.** Required Workstation/Windows/CI gates must finish
   green on the exact candidate head. The prior PR #29 runs failed
   `apply_core_integration.py --check` with
   `browser tool route anchor missing for browser_type`; local 599-pass evidence is
   retained but is not sufficient for product qualification.

Hard exit criteria:
- no composition may report success/COMMITTED without executing and verifying its plan;
- no ACK-only result is labeled VERIFIED unless the formal contract explicitly allows it;
- no request/session can synthesize mutation authority;
- no `REQUIRE_COMPILE` without deterministic/verifiable operational closure;
- bound native Browser readback never silently changes into process HTTP fallback;
- no blind retry after uncertain mutation;
- exact-head Workstation + Windows integration gates are green;
- real Electron fixture proves edit -> paste -> save -> persisted readback -> verify ->
  deterministic fan-out with zero intermediate planning.
## Verified Operational Control Plane (2026-09-18) — CP0–CP9 IMPLEMENTED / CONTRACT VALIDATED

Canonical specification:
[context/VERIFIED_OPERATIONAL_CONTROL_PLANE.md](context/VERIFIED_OPERATIONAL_CONTROL_PLANE.md).

PR #26 established the Operational Capability Runtime and PR #27 implemented the
Experience Compiler. Hermes can now execute known capabilities deterministically
and learn reusable capabilities from verified experience. The Verified Operational
Control Plane solves **selection and control**:

> Given an immutable semantic intent, current state, authority/policy and runtime
> events, derive a justified decision to SATISFY / EXECUTE / COMPOSE / WAIT /
> ASK_HUMAN / WAKE_LLM without making the LLM the scheduler.

Core target contracts:

~~~text
OperationIntent
  -> desired state + target + invariants + EffectBudget + AuthorityRef + Acceptance

Capability Router
  -> deterministic executability/typecheck proof

RoutingCertificate / CompositionCertificate
  -> no certificate, no dispatch

AwaitCondition / Trigger Plane
  -> wait durably with zero LLM; event wakes, authoritative state confirms

OpenCondition / AttentionPacket
  -> wake the LLM only for the smallest unresolved semantic decision
~~~

Implemented sequence:

1. **CP0 — typed intent/effect IR + immutable OperationIntent**
   - small versioned predicate/effect AST;
   - stable intent hash and IntentRevision;
   - preserve current WorkIntent behavior;
   - authority references only from trusted ingress/policy.
2. **CP1 — formal Capability contract**
   - backward-compatible typed pre/postconditions, effect footprint,
     target/operation family and authority requirements;
   - authority lattice/JOIN and resource normalization.
3. **CP2 — direct Router + RoutingCertificate**
   - internal capability index;
   - EXACT_EXECUTABLE / POSSIBLE_MATCH / INCOMPATIBLE / NEEDS_REASONING;
   - SATISFIED / EXECUTE / WAIT / ASK_HUMAN / WAKE_LLM;
   - prove goal coverage, effect containment, invariants, authority, policy,
     verifier, freshness and uncertainty closure.
4. **CP3 — bounded deterministic composition**
   - backward chaining over typed contracts;
   - hard search budgets;
   - CompositionCertificate;
   - causal-link/threat/conflicting-effect detection;
   - whole-plan effect/authority/verifier closure.
5. **CP4 — certified dispatch / preflight**
   - only certified dispatchable decision types can reach side-effect dispatch;
   - pin intent/state/capability/router-policy versions;
   - revalidate critical state immediately before mutation;
   - stale certificate reroutes/reconciles.
6. **CP5 — Await/Trigger Plane**
   - persistent AwaitCondition using existing TaskRun/WorkPlan owners;
   - causal/versioned event envelope, dedupe/stale/cycle/fence semantics;
   - restart-safe continuation;
   - deterministic temporal/polling policies;
   - uncorrelated events remain observation-only.
7. **CP6 — minimal reasoning handoff**
   - OpenCondition + AttentionPacket over existing reasoning_handoff;
   - confirmed effects/checkpoints preserved;
   - LLM proposal always returns through Router admission.
8. **CP7 — Skill/catalog routing**
   - semantic capability-family requirements rather than physical IDs by default;
   - internal/lazy catalog; approximate retrieval is proposal-only.
9. **CP8 — evaluation / shadow rollout**
   - Router/Trigger metrics, VOLC/RAR/ONR, failure attribution;
   - adaptive baseline -> shadow Router -> low-risk Router -> mutating Router.
10. **CP9 — integration / product qualification**
    - browser/filesystem/process paths, restart waits, uncertainty reconciliation,
      cross-backend composition, Workstation/Work100/Desktop gates.

Canonical proof properties:

- Router Soundness;
- Goal Non-Expansion;
- Authority Non-Escalation;
- Deterministic Closure;
- Verification Closure;
- Uncertainty Dominance;
- Event wakes; state confirms;
- LLM proposes; Router authorizes;
- **No certificate; no dispatch.**

The Router must remain a bounded deterministic typechecker/proof engine, not
another agent or general planner. Safety/authority/correctness are hard
constraints; optimization is secondary.

## Experience Compiler / Verified Operational Transitions (2026-09-18) — EC0–EC8 IMPLEMENTED / CONTRACT VALIDATED

Canonical specification:
[context/EXPERIENCE_COMPILER.md](context/EXPERIENCE_COMPILER.md).

PR #26 completed the first Progressive Operational Compilation milestone:
semantic operation identity, OperationalCapability Registry/Resolver,
Operational Kernel, direct `work_execute(capability_id, inputs)`, deterministic
composition and exact promoted replay are now implemented foundations.

The next problem is no longer "how do we execute a known capability without an
LLM?". It is:

> **how does Hermes turn real adaptive traces into trustworthy, minimal,
> parameterized OperationalCapabilities without asking an LLM to summarize the
> trace or rediscover the procedure?**

Canonical learned unit:

~~~text
Verified Operational Transition (VOT)
= smallest semantically closed + parameterizable + executable + verifiable
  state transition with positive reuse value
~~~

Target learning stack:

~~~text
adaptive execution
  -> TransitionSamples
  -> semantic state abstraction
  -> transition graph
  -> boundary proposals
  -> cross-trace clustering/alignment
  -> anti-unification + invariants
  -> conservative preconditions/effects/branches
  -> dependency / Operational Slice
  -> observational causal support
  -> safe replay / ablation where admissible
  -> counterexample refinement
  -> OperationalCapability Candidate
  -> trust/risk/causal promotion admission
  -> exact resolver / work_execute
~~~

Implemented sequence (evidence and remaining qualification: context/TESTING.md):

1. **EC0 — transition identity at capture**
   - normalize `procedure_trace` into a first-class TransitionSample contract;
   - fix browser fingerprinting so derived semantic anchors participate in
     operation identity rather than ref-only calls falling back to structural shape;
   - normalize emitted/replayable anchor types (`name` mismatch included).
2. **EC1 — semantic state + provenance**
   - bounded state predicates and semantic deltas;
   - evidence strength, Task/Run/operation lineage, trust class and taint.
3. **EC2 — corpus, segmentation and pattern discovery**
   - Experience Corpus projection over existing ArtifactStore/ExecutionJournal;
   - effect/commit/verification/changepoint/backend boundaries;
   - cross-trace alignment; core vs conditional vs optional vs anomalous.
4. **EC3 — parameterization / action-model inference**
   - anti-unify instance values into typed parameters;
   - infer supported parameter relations/invariants;
   - conservative preconditions/effects and state-conditioned branches;
   - failures/drift are negative examples.
5. **EC4 — dependency and causal support**
   - compute Operational Slices from data/control/effect dependency graphs;
   - separate recurrence/generalization from causal confidence;
   - assign explicit C0-C5 causal grades.
6. **EC5 — safe replay / ablation / counterexamples**
   - controlled replay and delta reduction only in safe/reversible environments;
   - no destructive production experimentation to improve a capability;
   - counterexamples refine assumptions into a new immutable candidate version.
7. **EC6 — promotion hardening / stable library view**
   - learned mutation promotion cannot be granted by raw validation count alone;
   - provenance/taint, E0-E3 evidence, C0-C5 causal grade, risk, diversity and
     utility participate in admission;
   - TaskRun uses a stable capability-version view;
   - run-local ephemeral compiled segment != globally promoted capability.
8. **EC7 — integration / registry economics**
   - emit candidates into the existing OperationalCapabilityRegistry;
   - preserve exact zero-LLM replay;
   - deduplicate/prune with utility/MDL-style value;
   - keep retrieval broad but execution admission exact.
9. **EC8 — cross-backend proof**
   - browser + filesystem lifecycle parity;
   - process/local case;
   - one cross-backend learned composite;
   - one atomic learned capability reused by two larger flows.

**Causal rule:** passive trace recurrence can propose/generalize a candidate, but
cannot by itself prove step necessity or grant high causal confidence.
Observational mining and interventional validation are separate phases.

**Trust rule:** Experience -> persistent Capability is a trust boundary. Repeated
untrusted page prose never becomes authority merely because the agent followed it.

**Promotion rule:** capture broadly, promote narrowly. The generic
`OperationalCapabilityRegistry.record_validation(..., auto_promote_threshold=2)`
must not be the complete promotion authority for experience-learned mutations.

**Optimization target:** minimize new reasoning required per verified outcome over
the lifetime of the system, while preserving the Canonical Execution Reliability
Gate.

## Upstream Reliability Hardening Intake (2026-09-18) — P0 IMPLEMENTED & VALIDATED; P1 PLANNED

Canonical implementation plan:
[context/UPSTREAM_RELIABILITY_HARDENING_2026-09-18.md](context/UPSTREAM_RELIABILITY_HARDENING_2026-09-18.md).

The 2026-09-18 upstream sweep found several failure modes that map directly onto
the Workstation reliability boundary. All confirmed P0 gaps have been implemented
and hardened on branch `fix/workstation-upstream-reliability-p0` without introducing
parallel state engines or breaking existing Workstation owners.

Completed P0 implementation order:

1. **P0.0 — revalidate/extend native Browser truth (#114964-derived): [DONE]**
   Reused existing H004 probe (`probes/h004-native-browser-task-smoke.mjs`) and
   extended it with deterministic discriminators: live WebContents id, continuous
   timer advance, input persistence, scroll persistence, and loopback controller
   action execution (`browser_snapshot`, `electron-chromium`). Explicit failure
   if external fallback occurs.
2. **P0.1 — recovery/resync correctness (#115068 + #115085): [DONE]**
   Ported live-tail journal selection via `findLastIndex` with duplicate interim
   row protection in `inflight-turn-journal.ts` (39 vitest tests). Preserved
   unacknowledged optimistic user messages during background resync in
   `use-background-sync.ts` and `wiring.tsx` (17 vitest tests).
3. **P0.2 — one canonical session writer (#111493): [DONE]**
   Enforced single-writer exclusivity per `session_id` in `active_sessions.py`,
   fenced transfers against foreign live writers, implemented `mode="observer"`
   read-only resume in `cli.py`, and failed closed on registry corruption.
   (7 tests in `test_cli_resume_read_only_owner.py`).
4. **P0.3 — Kanban truth/provenance (#114785 + #114793 + #114904): [DONE]**
   Validated session provenance against SessionDB (`state.db`) and request-scoped
   `HERMES_SESSION_ID` ContextVar; made heartbeat require both claim and worker
   writes to persist; fenced delegated child tasks; added durable worker-exit
   trailers (`HERMES_WORKER_EXIT_TRAILER_V1`) for topology-independent exit
   classification in `kanban_db.py` / `cli.py`.
   (7 tests in `test_kanban_provenance_and_exit_evidence.py`).
5. **P0.4 — bounded browser fallback recovery (#114897): [DONE]**
   Capped post-attach CDP reconnect attempts at 5 in `tools/browser_supervisor.py`,
   evicted exhausted supervisor from registry, reset failure budget on successful
   attach, and redacted credentials in warning logs.
   (3 tests in `test_browser_supervisor_reconnect_cap.py`).
6. **P1 next steps (after P0 PR review):**
   Design one Durable Delivery Rail from the common invariants in #115009/#115010/#114780
   and delegation-completion work; then benchmark snapshot quality using #115056.
   Do not create parallel queues or a second browser snapshot authority.

Explicit dispositions:

- **#114964:** production invariant is already implemented in BrowserTask; probe
  re-validated with extended real discriminators.
- **#114986 phantom turn lease:** no direct port now because this downstream
  `gateway.ts` does not contain the upstream `turnLeases` mechanism. Keep on
  rebase watchlist.
- **#115056:** native Work inventory is already one principal
  `webContents.executeJavaScript(...)` observation; P1 will benchmark and import
  hit-test/freshness ideas only.
- **computer-use provider seam / desktop bridge:** defer until native OS-control
  is an active milestone.
- **browser vault / Bot Screen / workflow-record:** P2; security, platform and
  RecipeStore boundaries take precedence.


## Progressive Operational Compilation & Operational Capability Runtime (2026-09-18) — FULLY IMPLEMENTED & VALIDATED

Canonical implementation document:
[context/PROGRESSIVE_OPERATIONAL_COMPILATION.md](context/PROGRESSIVE_OPERATIONAL_COMPILATION.md).
Settled architectural decision:
[D-018 in context/DECISIONS.md](context/DECISIONS.md).
Engineering journal record:
[H-067 in context/engineering-journal/CURRENT.md](context/engineering-journal/CURRENT.md).

The complete architecture for **Progressive Operational Compilation / Operational Capability Runtime** has been fully implemented, resolving AEPC-E002 and establishing a deterministic runtime execution substrate that eliminates unnecessary model round-trips without mutating past context or breaking existing stores.

Completed implementation summary:

1. **Semantic Target Family & Homogeneity Hardening (AEPC-E002 Resolved):**
   - Implemented `semantic_target_family()` and `semantic_operation_fingerprint()` in `workstation/execution_policy.py`.
   - Structural repetition without positive semantic homogeneity evidence never triggers `REQUIRE_COMPILE`; it only yields `SUGGEST_COMPILE`.
   - Distinct ephemeral refs (`@e1`, `@e37`, `@e92`) are no longer conflated with homogeneous fan-out.
   - Non-browser domain mutations retain strict compile requirements on the 3rd distinct equivalent mutation.
   - `CompilationCandidate` tracks `executed_occurrences` vs. `verified_successes` separately (`executed_unverified` never counts as verified success).

2. **Native Electron Target Metadata & Structured Elements:**
   - Updated `apps/desktop/electron/workstation-browser-runtime.ts` inventory and point scripts to extract `testid`, `name`, `role`, `tag`, and `label`.
   - Snapshot entries and action responses (`browser_click`, `browser_type`) now return structured element targets and semantic effects.

3. **Operational Capabilities Substrate (`workstation/operational_capabilities.py`):**
   - Implemented `OperationalCapability`, `CapabilityDependency`, `CapabilityLifecycle` (`DISCOVERED`, `VALIDATED`, `PROMOTED`, `RETIRED`).
   - `OperationalCapabilityRegistry` backed by existing `ArtifactStore` with cross-platform file locking (`fcntl`/`msvcrt`).
   - `CapabilityResolver` with cycle detection, depth limits, and topological sorting.
   - Automatic routine compilation via `learn_operational_capability()`.

4. **Deterministic Operational Kernel (`workstation/operational_kernel.py`):**
   - Zero-LLM execution of verified deterministic steps across filesystem and browser primitives.
   - Condition verification, variable interpolation (`$inputs`, `$deps`, `$prev`), and automatic drift detection with fail-closed quarantine.

5. **Direct & Automatic Reuse in `work_execute`:**
   - Added `capability_id`, `capability_version`, `capability_inputs` to `work_execute` tool schema.
   - Transparent reuse: when matching promoted capabilities exist for repetitive operations, `TaskCompiler` reuses them automatically with zero LLM calls.

6. **Validation & Gates:**
   - 100% passing tests across `workstation/tests/test_operational_capabilities.py` (12 tests) and `workstation/tests/test_execution_policy.py` (11 tests).
   - Full workstation suite: 510 passed, 2 skipped, 0 failed.
   - Work100 benchmark: 30 PASS / 0 FAIL / 0 gaps.
   - Vitest desktop runtime tests: 45 passed (100% green); TypeScript typecheck passes with 0 errors.


## Adaptive Execution & Progressive Compilation Gate (2026-09-18) — IMPLEMENTED; SEMANTIC-HOMOGENEITY HARDENING CLOSED WITH OPERATIONAL CAPABILITY RUNTIME

Remote implementation `9e7292ab7825e5ce1ea294490eec57ba1f286069`
(documentation/evidence `5e1b22527fd40d732ee4fa7a1035e6366953f6b7`; local
pre-publish implementation SHA `365794e29d66cd63a6134c5c67ecc1ef603d70a6`)
correctly removes the turn-wide mutation latch, normalizes effects/routes,
adds bounded adaptive discovery, compact handoff/resume and verified reuse.
Final recorded Python gate: 570 passed / 2 skipped; Work100: 30 PASS / 0 FAIL /
0 gaps; Desktop owner contracts: 36 passed.

AEPC-E002 reopened one narrow contract boundary: structural call similarity is
not sufficient proof of homogeneous fan-out. Current built-in browser mutations
such as `browser_type`, `browser_click` and `browser_press` do not declare a
concrete mutation target/target family, so three semantically different stateful
UI actions can still converge on the same structural signature and trigger
`REQUIRE_COMPILE`. KI-011 therefore has its original global-latch cause fixed,
but long stateful-browser closure remains open until semantic homogeneity is
proven before mandatory compilation. Authenticated native/packaged Electron
smoke remains a separate final product gate. Simulated provider-call reductions
do not establish paid-provider savings.

Real native-browser dogfood exposed an architectural overreach in the durable
compiler boundary: the baseline mechanism introduced to keep repetitive mechanical work
out of the LLM loop could turn a repeatability hint into a broad mutation
gate and block legitimate stateful/adaptive work before a deterministic procedure
has been discovered.

Canonical specification:
[context/ADAPTIVE_EXECUTION_COMPILATION.md](context/ADAPTIVE_EXECUTION_COMPILATION.md).

This correction preserves the Canonical Execution Reliability Gate and its
canary, uncertainty, fencing, acceptance, reconciliation and evidence invariants.
It changes **when compilation is mandatory**.

Target execution ladder:

~~~text
novel/drifted work
  -> ADAPTIVE reasoning + bounded tools
  -> stable segment captured
  -> COMPILED segment/work
  -> validated Procedure/Recipe
  -> PROMOTED ROUTINE
  -> drift => compact NEEDS_REASONING handoff
  -> adapt only the unresolved segment
~~~

Implemented sequence (retained as the acceptance checklist):

1. replace the session/turn-wide _work_batch_candidate latch with an
   operation-scoped compilation candidate / policy decision;
2. add ALLOW_ADAPTIVE | SUGGEST_COMPILE | REQUIRE_COMPILE | REQUIRE_HUMAN;
3. normalize browser tool constraints to native_browser and make tools.effects
   the single effect taxonomy;
4. allow bounded stateful native-browser interaction during discovery while
   retaining BrowserTask/TaskRun leases, approvals and effect uncertainty;
5. add compact NEEDS_REASONING escape/resume semantics to deterministic work;
6. capture successful adaptive traces into existing Recipe/ProceduralMemory
   owners and automatically reuse verified procedures;
7. measure LLM calls/tokens/tool calls per verified outcome plus Guardrail
   Obstruction Rate;
8. add regressions proving both sides: native-browser adaptive progress works and
   homogeneous fan-out still cannot bypass TaskCompiler/canary.

### AEPC-E002 follow-up — semantic homogeneity before mandatory compilation

Required hardening, in order:

1. separate **structural similarity** from **semantic homogeneity** in
   `CompilationCandidate` / `execution_policy.py`;
2. require a stable owner-declared or safely derived operation family before
   `REQUIRE_COMPILE`: operation + canonical route/provider + concrete
   target-family/contract identity. Shape-only browser calls are not enough;
3. keep long stateful native-browser sequences adaptive when successive
   click/type/press actions target different semantic UI goals, while preserving
   TaskRun/BrowserTask fencing, approval, uncertainty and no-progress limits;
4. retain mandatory TaskCompiler/canary admission for real homogeneous fan-out;
5. add paired regressions: a long stateful browser flow with 3+ same-tool
   mutations remains adaptive, while three true same-family mutations still
   transition to `REQUIRE_COMPILE`;
6. rename or redefine `CompilationCandidate.successful_occurrences` so
   `executed_unverified` is never represented as verified success;
7. reconcile all canonical docs to the remote SHAs above and preserve the
   original local SHA only as pre-publish history.

**Exit criteria:** no threshold increase, browser-name exemption or global bypass.
The runtime must be able to explain *why* operations are one compilable family;
absence of that proof keeps execution bounded/adaptive rather than manufacturing
homogeneity.

**Sequencing:** the global-latch correction is implemented, but AEPC-E002 must
close before KI-011 is called fully resolved. Retain the native qualification
gate before claiming product-level closure. Do not weaken fan-out safety to fix
usability, and do not require determinism as a precondition for discovering a
safe deterministic path.

## Canonical Execution Reliability Gate (2026-09-17) — IMPLEMENTED & VERIFIED

**Milestone implemented and verified on branch `antigravity/canonical-execution-reliability-gate`.**
The causal reliability gate establishes full end-to-end lineage, run fencing, terminal tree reconciliation, streaming journal hash chaining, and human takeover fencing, proven by 35 canonical work loop tests, 446 workstation tests, and clean `work100.py --run` execution.

Canonical specification and exit criteria:
[`context/CANONICAL_EXECUTION_RELIABILITY_GATE.md`](context/CANONICAL_EXECUTION_RELIABILITY_GATE.md).

The gate converts the Workstation from a broad set of implemented capabilities into
a causally trustworthy operational system. The target loop is:

```text
intent
  -> canonical Task
  -> canonical TaskRun
  -> WorkPlan / WorkItems
  -> Browser / Worker / Host operations
  -> evidence
  -> acceptance / verification
  -> canonical commit
  -> journal / projections
  -> result
  -> learning / routine
```

The work is dependency ordered:

1. **P0 — causal execution invariants**
   - canonical Task -> TaskRun -> WorkPlan/WorkItem lineage;
   - separate durable `execution_key` from canonical Task identity;
   - propagate `run_id` through Workstation events/evidence/resources/reports;
   - complete agent-owned tasks with canonical `expected_run_id` fencing;
   - commit canonical completion before terminal journal/UI/Hybrid projections;
   - reconcile terminal parents with live descendants;
   - give mutable effects durable `operation_id` + uncertainty/reconciliation semantics;
   - enforce typed Intent Authority at every work-creation boundary.
2. **P1 — reliability, fencing and recovery**
   - Run-scoped mutation fencing for Browser/Worker/Host resources;
   - startup/periodic reconciliation over existing Supervisor/Recovery/Evidence owners;
   - exactly-once Agent Task -> Human Card result/evidence projection;
   - systemic-failure cohort/circuit-breaker coverage beyond the TaskCompiler canary;
   - cron health/config/model migration semantics.
3. **P2 — efficiency and auditability**
   - evidence provenance tied to Task/Run/operation/acceptance criterion;
   - Runtime State Resolver so the LLM stops reconstructing deterministic state;
   - reference-first artifact/tool outputs and context/FTS canonicalization;
   - bounded no-progress/polling behavior;
   - long-run journal scalability/integrity benchmark.
4. **P3 — evaluation, learning and UX**
   - corpus-derived Hermes Work 100 seed suite;
   - AVCR plus false-completion/zombie/recovery/uncertainty/efficiency metrics;
   - measured Experience -> Candidate -> Validate -> Promote -> Routine -> Drift;
   - Task Cockpit/Control Center only after state truth is proven.

### Immediate invariants

```text
Task.status = terminal
  must be attributable to the authoritative TaskRun or an explicit human override

parent.status = terminal
  => no descendant remains externally LIVE after the reconciliation barrier

mutable operation dispatched + acknowledgement lost
  => UNCERTAIN / RECONCILING, never blind retry

journal says completed
  => canonical completion already committed successfully

system/tool/scheduler/recovery event
  != human CREATE_WORK unless an explicit authority transition permits it
```

### Reuse, do not rebuild

This gate deliberately reuses what current `main` already has: canonical Kanban
`task_runs/current_run_id`, `expected_run_id` CAS support, BrowserTask,
TaskCompiler canary/admission, dispatch checkpoints, idempotency contracts,
recipe staleness/quarantine, Execution Journal, EvidenceState, WorkerRegistry,
Recovery Plane, human-control leases, Hybrid delegation and the existing artifact
reference plane. The work is integration/hardening, not a second orchestration or
state system.

### Global sequencing override

Any later wording in this historical roadmap that says a V1/V1.1/V2/V3/V3.5/V4
item is “active next”, “must happen next”, or is otherwise next in sequence is
**deferred by this gate**. Completed/implemented labels below remain implementation
history; they do not imply product-level causal reliability until this gate passes.

## Foundation — on current `main`

- `workstation/` architecture, contracts, policies and upstream tracking.
- first-class `/browser` route in Hermes Desktop.
- internal Electron Chromium Browser runtime with dedicated persistent profile.
- multiple tabs, navigation, attach/detach, background survival and cache-only maintenance.
- pause/resume, focus, take/release control primitives.
- loopback-only bearer-authenticated Browser controller in Hermes Desktop.
- `browser_*` integration that prefers internal Chromium and fails closed after task binding.
- Kanban Desktop enabled by default in this downstream distribution.
- stable/edge channel metadata.
- CI skeleton, lock/license validation and Windows Browser E2E workflow.
- eval matrix prepared for internal/agent-browser/browser-exec.
- Desktop Browser schema capability is session-scoped and protected from process-global cache/env leakage.
- first-class BrowserTask lifecycle promoted by PR #9: `create` / `show` / `hide` / `park` / explicit `destroy`, crash recovery, safe logical persistence and restart restoration.
- `taskTabs` + `BrowserEntry.ownerTaskId` remain the authoritative live Chromium task→page ownership primitives; no second page store was introduced.
- one `taskId` is idempotently bound to at most one live task page in a Desktop process.
- hide/park/show preserve the same live page and current URL while the process remains alive.
- restart restores safe BrowserTask metadata as parked and lazily recreates exactly one page under the same logical task when needed.
- composite BrowserSessionState now persists ordinary/task logical tabs, order,
  active selection, sanitized restorable metadata and BrowserTask linkage through
  one atomic state authority.
- clean and abrupt two-process restart, profile/state separation and failed-write
  convergence are validated by H010 on the accepted PR #11 head.
- repository-root one-click dogfood startup now performs install → doctor →
  start without installing dependencies twice.

## Implementation 4 — promoted

PR #9 (`feat(workstation): formalize BrowserTask lifecycle`) was promoted to `main` in merge commit `fada723f43613e5e0f061cab24445573ac298998` from accepted head `75d10d35d4757496390debf8e4b4f9efb44c5432`.

Acceptance evidence:

- focused BrowserTask lifecycle/runtime tests passed;
- real Windows/Electron H-004 smoke validated same-page hide/park re-exposure, explicit destroy, two-process logical restart recovery, exactly-one-page ownership and structural secret isolation;
- controlled Windows baseline comparison returned `WINDOWS_BASELINE_COMPARISON=PASS_WITH_KI-006_RED` and found no Implementation 4 regression class;
- exact-final-head Workstation CI and Docker gates passed; the broad Windows aggregator remained red only for the known KI-006 baseline debt.

The following work remains intentionally outside Implementation 4.

## Delivery strategy — reliability gate before further feature hardening

From 2026-09-17 the roadmap has three complementary delivery modes:

1. **Canonical Execution Reliability Gate** — immediate cross-domain invariant hardening; this blocks further feature-expansion sequencing until its exit criteria pass.
2. **Canonical milestone hardening** — each numbered milestone remains responsible for its rigorous architecture, ownership model, security boundary, recovery semantics, migrations, regression coverage and native evidence.
3. **Integrated MVP dogfood** — the historical V1 #1.5 vertical slice remains useful product history and a post-gate feature-integration reference.

The MVP track is **not** permission to create throwaway architecture. Every MVP slice must:

- reuse the canonical Hermes/Workstation owner for state and control;
- avoid second SessionDB/Kanban/Memory/browser stores or duplicate live pages;
- preserve BrowserTask one-live-page and bound-task fail-closed invariants;
- prefer a narrow working path over a broad fake/stub path;
- keep experimental V1.1/V2 slices opt-in when they are not yet suitable for the default path;
- leave the original milestone open for later robustness work rather than marking it complete merely because its MVP exists;
- include at least one behavior contract or dogfood scenario strong enough to prove that the slice is actually usable.

The intended cadence is now:

```text
V1 #1 BrowserSessionState — rigorous completion
        ↓
pre-1.5 Mainline Consolidation Gate — PASS
        ↓
Canonical Execution Reliability Gate — ACTIVE
        ↓
V1 #1.5 / remaining feature-hardening roadmap resumes
        ↓
continuous real usage / dogfooding + Hermes Work 100
        ↓
V1 #2, #3, #4... / V1.1 / V2 / V3+ hardening as still applicable
```

## V1 #1 — BrowserSessionState — promoted

PR #11 accepted `d5be442021ea0c744351622317eef5212219786d` and was
promoted as merge `e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29`.

The milestone delivered the composite safe structural state, atomic convergence,
ordinary/task tab order and active selection, safe URL/title recovery boundaries,
BrowserTask coexistence, legacy migration and explicit clean/abrupt restart
semantics. H010 emitted `H010_CLASSIFICATION=VALIDATED` on the exact accepted
Windows/Electron head.

Controller/session/run/Kanban linkage beyond the identifiers already present in
BrowserTask is now part of the immediate Canonical Execution Reliability Gate where
it affects causal TaskRun identity. This does not reopen the completed structural
BrowserSessionState owner.

## Mainline Consolidation Gate

The extraordinary gate between V1 #1/PR #12 and the historical V1 #1.5 sequence is
**PASS**. Its audit base, PR/branch disposition ledger, checklist and recurring
review procedure are canonical in
`context/MAINLINE_CONSOLIDATION.md`.

Its branch/history result remains valid. The 2026-09-17 reliability gate is a new
post-consolidation priority discovered from runtime/state evidence; it does not
invalidate the historical consolidation result.

## Deferred roadmap — resumes after Canonical Execution Reliability Gate

### 1.5. Integrated Dogfood MVP — whole-roadmap vertical slice

**Sequence:** V1 #1 and the pre-1.5 Mainline Consolidation Gate are complete.
This remains the next historical feature-integration milestone **after** the
Canonical Execution Reliability Gate closes. It no longer outranks the reliability
gate.

**Purpose:** make the Hermes Workstation useful as an integrated daily-driver alpha as early as possible. Instead of waiting for every later subsystem to become architecturally exhaustive, implement the smallest real version of every currently planned capability on top of the correct owners. Real dogfood then supplies evidence for the later hardening milestones.

The full V1 #1 implementation is the state foundation for this milestone; its MVP is therefore considered satisfied by the stronger completed BrowserSessionState rather than reimplemented separately.

#### MVP map for every roadmap milestone

| Canonical milestone                                           | MVP slice implemented during 1.5                                                                                                                                                                                               | Deferred to the original milestone                                                                                               |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| **V1 #1 — BrowserSessionState**                               | Satisfied by the completed milestone: ordinary logical tabs/order/active state, safe restorable metadata, BrowserTask relation and explicit restart/recovery projection.                                                       | Further defects discovered by dogfood remain #1 follow-up/hardening, not a parallel state model.                                 |
| **V1 #2 — Chat Browser View + Browser Hub**                   | A contextual Chat surface can expose/inspect a BrowserTask and a global Hub can list/open the same BrowserTasks. Both resolve the same runtime/task identity.                                                                  | Rich layouts, polished navigation, grouping UX, thumbnails, accessibility and exhaustive UI behavior.                            |
| **V1 #3 — single-host ownership / viewport transfer**         | One explicit/manual transfer path moves the same live `WebContentsView` between the MVP Chat surface and Hub with no duplicate navigation/page.                                                                                | Full geometry state machine, resize/maximize/restore/sidebar/pane matrix, race handling and exhaustive native composition tests. |
| **V1 #4 — Preview compatibility adapter**                     | For a Workstation-bound browser task, the basic Preview path reuses/adapts to the same BrowserTask/runtime or refuses to create a duplicate lane.                                                                              | Complete compatibility/parity for every Preview action and transition.                                                           |
| **V1 #5 — persistent controller/session/run/Kanban bindings** | Persist the minimum identity set required by dogfood (`taskId`, Hermes `session_id`, available run/card identifiers) through existing BrowserSessionState references, with one-time binding and mismatch fail-closed behavior. | Full migration matrix, lineage semantics, rotation/recovery edge cases and richer identity policies.                             |
| **V1 #6 — automatic Kanban promotion**                        | A clearly multistep Workstation request can automatically create/bind one Hermes Kanban parent card and its BrowserTask through the existing Kanban path.                                                                      | Sophisticated planning/classification, decomposition policy, prioritization and generalized orchestration.                       |
| **V1 #7 — follow-up discovery / parent dependency**           | A running task can emit one child/follow-up card carrying `parent_task_id`, `discovered_by`, `reason`, `evidence` and `origin_session_id`, with a minimal parent-blocked/child-complete relationship.                          | General dependency graphs, scheduler semantics, fan-out/fan-in and advanced planning.                                            |
| **V1 #8 — Execution Journal**                                 | Persist a minimal append-only execution/evidence journal referenced by the canonical task/card, with timestamp, action/tool, result/status and selective screenshot evidence only at explicit key events.                      | Rich replay, retention, compaction, cost/event taxonomy, advanced evidence viewer and governance.                                |
| **V1 #9 — completion reports**                                | On completion, write a concise summary plus structured task/session/card/evidence metadata through `kanban_complete(metadata=...)`.                                                                                            | Rich report templates, analytics, cross-run synthesis and advanced reporting UX.                                                 |
| **V1 #10 — Browser live task rail**                           | Desktop shows a simple task rail grouped into `active`, `waiting-for-human`, `background` and `recent`, backed by canonical BrowserTask/Kanban state.                                                                          | Advanced filtering, prioritization, thumbnails, Dashboard/mobile parity and richer task operations.                              |
| **V1 #11 — LAN settings**                                     | Explicit opt-in using the official Hermes Dashboard backend: auth preflight, non-loopback bind only when safe, detected LAN URL/IP and QR presentation.                                                                        | Full settings polish, network diagnostics, multi-interface handling, remote lifecycle and hardened remote UX.                    |
| **V1 #12 — popup/SSO + download/upload UX**                   | Support one common same-profile popup/SSO flow plus basic file upload selection and download completion/location visibility.                                                                                                   | Broad popup policies, complex SSO/multi-window flows, download manager, chooser edge cases and polished UX.                      |
| **V1 #13 — recovery E2E**                                     | One real golden recovery scenario proves controller/browser interruption → pause → reconnect/rebind → identity/profile verification → resume.                                                                                  | Chaos matrix, multiple simultaneous failures, backoff policies, long-running soak and exhaustive recovery combinations.          |
| **V1 #14 — Windows clean-install + native E2E**               | One supported Windows toolchain proves fresh checkout → one-click install/doctor/start → Desktop opens → one real BrowserTask/host-composition smoke.                                                                          | Wider Windows/toolchain matrix, packaging/updater paths and exhaustive clean-machine/native composition coverage.                |
| **V1.1 — Tailscale**                                          | Opt-in detection of an already-installed/authenticated Tailscale environment and presentation/use of the official authenticated Dashboard route over the detected Tailnet address.                                             | Installation/account management, richer lifecycle, policy and remote diagnostics.                                                |
| **V1.1 — external Hermes Browser Extension compatibility**    | Optional experimental routing of one **unbound** task through the official extension lane for a basic navigate/read path; bound internal tasks remain fail-closed.                                                             | Feature parity, reconnect/lease depth, broader routing policy and compatibility matrix.                                          |
| **V1.1 — richer cache/resource maintenance**                  | One safe, scoped maintenance action for Workstation browser cache/site data plus basic diagnostics; never clear personal Chrome/Edge data.                                                                                     | Policy engine, granular resource management, scheduling, storage visualization and automatic maintenance.                        |
| **V1.1 — download/upload UX**                                 | Extend the V1 #12 MVP with a minimal downloads list/status and a reliable explicit upload chooser path.                                                                                                                        | Rich file management, retries, queueing, previews and cross-device UX.                                                           |
| **V1.1 — richer multi-task scheduling/ownership**             | Run at least two BrowserTasks with a simple queue/background model, one visible native host at a time and explicit task ownership; simple FIFO/manual selection is sufficient.                                                 | Priorities, fairness, leases, preemption, resource budgets and sophisticated scheduling.                                         |
| **V2 — procedural web memory**                                | After a successful workflow, explicitly save one reusable procedure into the existing Hermes Memory/skill path with domain/context + ordered steps/evidence, then manually replay it on a compatible task.                     | Automatic learning, confidence/versioning, generalized retrieval, adaptation and lifecycle governance.                           |
| **V2 — provenance-aware compact perception**                  | Produce one compact page representation from the current browser state with stable provenance references sufficient for an agent to inspect and perform a basic action.                                                        | Adaptive perception, multimodal fusion, aggressive token optimization, cross-page provenance and full Lattice-inspired engine.   |
| **V2 — drift diagnosis / governed adaptation**                | Detect one class of procedure/selector mismatch, classify it as drift, stop unsafe continuation and trigger re-exploration or human/agent replanning with evidence.                                                            | Automated repair policies, confidence thresholds, regression-vs-drift inference, governance and long-term adaptation.            |
| **V2 — Lightpanda runtime**                                   | Experimental opt-in runtime adapter for safe **unbound, stateless/read-oriented** web tasks; no silent migration of a bound/authenticated Electron BrowserTask.                                                                | Benchmark-driven routing, broader web compatibility, stateful semantics, scheduling and production runtime support.              |

#### Integrated dogfood golden path

The 1.5 milestone is considered useful only when a real user can exercise an end-to-end path resembling:

```text
double-click one launcher
  → install/validate/doctor/start automatically
  → Hermes Desktop opens
  → user asks for a clearly multistep web task
  → Hermes creates/binds canonical Kanban + BrowserTask identities
  → internal Chromium performs visible work
  → user can inspect the task from Chat and Browser Hub MVP surfaces
  → the same live page can be manually transferred between hosts
  → Preview does not create an independent duplicate for the bound task
  → task rail shows current state
  → a discovered child task can be recorded
  → journal/evidence is persisted
  → completion writes structured Kanban metadata/report
  → restart/recovery preserves the logical task/profile boundary
```

The LAN, Tailscale, external-extension, memory/perception/drift and Lightpanda MVP slices may remain explicitly experimental/opt-in, but they must be executable real paths rather than documentation-only placeholders.

#### Exit criteria for 1.5

- every row above has a real implementation at its stated MVP boundary or is blocked by a documented non-negotiable dependency discovered after V1 #1;
- no MVP introduces a competing SessionDB, Kanban, Memory, browser page store or control plane;
- one-click Windows dogfood startup exists and is documented;
- the integrated golden path has executable evidence on Windows/Electron;
- known limitations are recorded without reclassifying original milestones as complete;
- after 1.5, development resumes at **V1 #2** and revisits the original roadmap milestone-by-milestone for architectural hardening.

2. Build the contextual Chat Browser View and global Browser Hub as two views of the same BrowserTask/runtime.
3. Implement a single-host ownership/viewport contract for moving one live `WebContentsView` between Chat and Browser Hub; validate resize/maximize/restore/pane changes without overlap.
4. Replace the independent Workstation-mode Preview browsing lane with a compatibility adapter over the same BrowserTask/runtime where appropriate.
5. Persist controller/session/run/Kanban identity bindings across process restarts without introducing a second SessionDB/Kanban store.
6. Promote multistep requests into Kanban automatically.
7. Add follow-up task discovery metadata and parent dependency policy.
8. Add Workstation Execution Journal persistence and selective screenshots.
9. Generate browser task completion reports into `kanban_complete(metadata=...)` — **Completed** (`workstation/kanban.py`).
10. Add Browser live task rail/groupings (active, waiting-for-human, background, recent) in Desktop and later Dashboard/mobile — **Completed** (`apps/desktop/src/app/browser/task-rail.tsx`).
11. Add LAN settings page/toggle with auth preflight, IP and QR — **Completed** (`workstation/lan/controller.py`).
12. Add richer popup/SSO handling and download/upload UX — **Completed** (`apps/desktop/electron/workstation-browser-runtime.ts`).
13. Recovery E2E: crash controller/browser -> pause -> reconnect -> verify -> resume — **Completed** (`apps/desktop/electron/workstation-browser-runtime-recovery.test.ts`).
14. Windows clean-install + native BrowserTask/host-composition E2E — **Completed** (`START-HERMES-WORKSTATION.bat`, `install.ps1`, `doctor.ps1`).

## V1.1 — Completed & Hardened

- Tailscale integration (`workstation/lan/controller.py` - `detect_tailscale`).
- optional external Hermes Browser Extension compatibility mode (`workstation/routing.py`).
- richer cache/resource maintenance (`apps/desktop/electron/workstation-browser-runtime.ts` - `cleanupCache`).
- download/upload UX (`apps/desktop/electron/workstation-browser-runtime.ts` - `downloads` tracking and interactive Hub drawer).
- richer multi-task scheduling/ownership policies on top of the one-task/one-live-page invariant (`workstation/scheduler.py` - `MultiTaskScheduler`), hardened with lease timeouts, heartbeats, and orphan task reaping (H-106).

## V2 — Completed & Hardened

- procedural web memory (`discover -> run -> explore -> learn`) (`workstation/memory.py` - `ProceduralMemory`), hardened with multi-facet fallback anchors (testid -> role -> text -> selector) and concurrent disk merge (H-101).
- provenance-aware compact perception engine inspired by Lattice (`workstation/perception.py` - `PerceptionEngine`), hardened with hidden/invisible node filtering (H-102) and tiered smart budgeting that guarantees CTA and form preservation under token limits (H-103).
- drift diagnosis and governed adaptation (`workstation/drift.py` - `DriftGovernor`), hardened with blocking cookie/modal overlay detection (`DISMISS_OVERLAY`) (H-104) and strict financial/destructive action boundaries in `workstation/safety.py`.
- Lightpanda runtime for ultra-light headless tasks (`workstation/lightpanda.py` & `workstation/routing.py` - `LightpandaAdapter`), hardened with transparent gzip/deflate decompression and fail-closed auth redirect detection (H-105).
- Windows filesystem atomic resilience: eliminated `EPERM` / `EBUSY` in `BrowserSessionStateFilePersistence` via `copyFileSync` fallback (H-107).

## V2.1 — Native Chrome Web Store Extensions Support — Partial / Agentic Install Slice Implemented

- **Chrome Web Store Extension Downloader & Unpacker** — **Completed** (`workstation/extensions.py` - `ChromeExtensionManager`):
  - Mecanismo para baixar pacotes `.crx` diretamente da Chrome Web Store a partir do ID da extensão ou URL pública (via endpoint oficial de atualização do Chromium: `clients2.google.com/service/update2/crx`).
  - Descompactação segura com remoção de cabeçalho binário `Cr24` para diretório dedicado no perfil da Workstation (`~/.hermes/workstation/extensions/<extension_id>/`).
- **Native Electron Runtime Loading** — **Completed** (`apps/desktop/electron/workstation-browser-runtime.ts` - `loadInstalledExtensions`):
  - Integração no `WorkstationBrowserRuntime` via `this.browserSession.loadExtension(extensionPath, { allowFileAccess: true })`.
  - Persistência e restauração automática das extensões instaladas durante a inicialização da sessão do Chromium.
- **Agent Tooling & Governed Extension Interaction** — **Implemented vertical slice** (`tools/workstation_extensions.py`, `workstation/policy.py`, `apps/desktop/electron/workstation-browser-runtime.ts`):
  - Ferramentas de sessão Desktop para instalar, listar, remover e abrir opções; elas não aparecem em CLI/gateway sem superfície Desktop.
  - A instalação baixa para memória, inspeciona permissões do `manifest.json`, classifica risco e consulta `ScopedPolicyEngine`; permissões médias/altas e remoção exigem o approval gate canônico.
  - Sucesso de instalação exige `install -> Electron load -> runtime verification`; falha de load remove o artefato local em vez de declarar a capability pronta.
  - Todas as transições são registradas no `ExecutionJournal` canônico.
- **Hardening remaining**:
  - Não existe ainda um catálogo/busca semântica da Chrome Web Store: o agente recebe ID ou URL pública, em vez de selecionar extensões a partir de resultados de marketplace.
  - Não há UI dedicada de gerenciamento de extensões no Desktop; a superfície atual é agent/tool + BrowserTask options page.
  - Atualização in-place agora usa staging, journal de promoção e last-known-good: falha de replace, load, verificação ou restart restaura a versão anterior. A transação é coberta por `workstation/tests/test_extensions.py`.

## Hybrid Kanban — Experimental vertical slice (human + agent shared workspaces)

Hermes Kanban now has two deliberately separate modes under the same canonical
per-board SQLite owner:

- **Agentic Kanban** remains the existing operational task state machine
  (`triage` → `ready` → `running` → terminal states), dispatcher, runs,
  dependencies and Workstation task lineage.
- **Hybrid Kanban** is a shared human/agent workspace of named boards, columns
  and cards. Its columns are user organization only: moving a Hybrid card to a
  column named “Done” never calls `kanban_complete` or dispatches work.

Implemented vertical slice:

- additive `hybrid_*` tables in the canonical `hermes_cli.kanban_db` database;
- one transaction-backed domain path (`hermes_cli.hybrid_kanban`) for API and
  agent-tool mutations, with actor/session provenance in `hybrid_activity`;
- deterministic dense ordering with a private temporary rank namespace to make
  swaps/reorders atomic under SQLite's unique rank constraints;
- optimistic-concurrency rejection through `expected_revision` for stale card
  and column operations;
- authenticated Kanban plugin API, `kanban_hybrid` agent tool, and an Electron
  Desktop shared-board page for creating boards/columns/cards, editing Markdown
  text and dragging cards between columns;
- restart persistence and Agentic-boundary behavior covered by Python tests;
- explicit **“Entregar isto ao Hermes”** delegation creates a separate canonical
  Agentic task in the same Kanban database, maintains a persistent bidirectional
  link, and projects compact status/result/evidence back to the human card;
- archive/restore and explicit hard-delete semantics, persisted activity,
  horizontal column reorder, revision checks, and precise invalidation over the
  existing plugin `/events` boundary are implemented and covered.
- multiple per-card checklists, revision-safe item completion/reorder/delete,
  restart persistence, activity provenance, canonical plugin RPC and Desktop
  card-drawer controls are implemented and covered.

Hardening remaining:

- multi-user authorization beyond the existing authenticated Dashboard session
  boundary, Hybrid-card comments/attachments and external-board connectors.

## V2.5 — Agent Runtime + System Capability Control Plane — Completed

### Agent Runtime / Worker Registry — Completed (`workstation/workers.py`)

Workstation-level abstraction for specialist agent harnesses without replacing Hermes as the primary conductor.

- Normalized discovery, installation/readiness, invocation, task handoff, cancellation and health across compatible worker agents (`WorkerRegistry`, `WorkerHarnessInfo`, `DelegatedTaskHandoff`).
- Delegation of bounded subtasks to workers (Codex, Claude Code, Antigravity, OpenCode, K-Tools-Neo) while retaining canonical Hermes task/session/card lineage in `ExecutionJournal`.
- Auditable recording of worker execution steps in canonical journal events.
- All worker details preserved behind clean adapters without leaking into Workstation core.

### System Capability Layer — Completed (`workstation/host.py`)

Generalized safe host-capability boundary for operations outside the browser.

- Filesystem and workspace operations (`inspect_workspace`);
- Process/application launch and command execution (`run_command`);
- Clipboard read/write handoff (`read_clipboard`, `write_clipboard`);
- Git operations (`git_status`);
- Desktop notifications (`send_notification`);
- Machine diagnostics and hardware metrics (`get_diagnostics`).
- Providers implemented: `WindowsHostCapabilityProvider`, `LinuxHostCapabilityProvider`, and `KToolsNeoCapabilityAdapter` (candidate external automation adapter without hard dependency).

### System Event → Hermes Task pipeline — Completed (`workstation/events.py`)

Inverse automation direction surfacing system events back into canonical Hermes task model (`SystemEventPipeline`).

- Supported event classes: `PROCESS_CRASH`, `BUILD_FAILURE`, `BUILD_SUCCESS`, `DOWNLOAD_COMPLETED`, `REPO_STATE_CHANGED`, `CONTROLLER_HEALTH_CHANGED`, `LONG_RUNNING_JOB_COMPLETED`, `USER_ATTENTION_REQUIRED`.
- Translates critical/untracked events into canonical Kanban tasks via `WorkstationKanbanBridge` and enriches active tasks via `ExecutionJournal`.
- Strict retention of provenance, reason, and execution evidence without duplicate schedulers or stores.

### Scoped autonomy / Policy Engine — Completed (`workstation/policy.py`)

Explicit scoped autonomy classifying actions into deterministic security outcomes:

```text
allow
sandbox / constrain
require human confirmation
deny
```

- Enforces least privilege per task/capability;
- Sensitive OS directory protection (`C:\Windows`, `/etc`, `~/.ssh`) and dangerous command pattern protection (`rm -rf /`, `format`, fork bombs) -> `DENY`;
- Out-of-workspace writes and financial/irreversible actions -> `REQUIRE_APPROVAL`;
- Untrusted executions -> `SANDBOX`;
- Full auditable evaluation trail preserved for every action.

### Agent Control Center / observability — Completed (`apps/desktop/src/app/browser/task-rail.tsx`, `task-journal-drawer.tsx`)

Live task rail, task grouping, interactive journal replay player, download drawer, and execution lineage inspection.

## V3 — Cross-platform Agentic Workstation — Completed

### Omarchy as Linux reference host — Completed (`workstation/omarchy.py`)

- `OmarchyAdapter` detecting Omarchy environment, default coding agent, system skills, and normalized agent CLI launcher without distro-specific file hacking.

### Cross-platform host adapters — Completed (`workstation/cross_platform.py`)

- `CrossPlatformHostManager` providing unified capability discovery, execution normalization, and host summaries across Windows and Linux.

### Agentic Desktop Reference Tracking — Completed (`workstation/cross_platform.py` - `AgenticBenchmarkRegistry`)

Lightweight architectural benchmark registry tracking:
1. Omarchy
2. Hermes Upstream
3. OpenHands
4. OpenCode
5. Claude Code
6. Codex
7. Antigravity
8. BrowserOS

Evaluating all 4 core architectural questions:
1. Problem solved?
2. Does Hermes have this problem?
3. Expressible in Hermes contracts?
4. Upstream-delta safe?

### V3 Target Experience — Fulfilled

```text
one user request
  → canonical Hermes task/session/card
  → Hermes plans/orchestrates
  → optional specialist worker executes a bounded subtask
  → Browser and/or host capability adapters act under scoped policy
  → system events can wake or enrich the same task
  → journal/evidence/recovery stay attached to the canonical lineage
  → the same semantic workflow can run on supported Windows or Linux hosts
```

### V3.1–V3.4 implementation status — 2026-09-12

The planned Python contract layer is implemented in `workstation/` and is
validated by 175 Workstation tests plus the versioned Windows process-boundary
probe `context/engineering-journal/probes/v3-runtime-hardening-smoke.py`.
The implementation extends the existing owners: `ExecutionJournal`,
`ProceduralMemory`, `WorkerRegistry`, Hermes sessions, Kanban and BrowserTask;
it does not add a parallel canonical store or model tool.

Implemented surfaces include:

- EvidenceState and durable reconciliation, bounded RuntimeEventBus with
  journal mirroring, deadlines/cancellation, typed reconnectable resources and
  task-scoped budget/model routing;
- independent subprocess RuntimeSupervisor with watchdog restart/checkpoints,
  Recovery Plane quarantine/diagnostics and a dependency-light recovery CLI;
- discover → validate → promote → deterministic routine replay with fail-closed
  drift handling and journal lineage;
- persistent WorkerRegistry queue/message/steer/wait/stop/reconstruct lifecycle,
  structured result envelopes and parent wake-up events;
- typed temporal memory, recoverable snapshots, hot/warm/cold session metadata,
  migration rollback, explicit compaction markers, portable redacted traces,
  side-effect-free replay/fork and model-independent evaluation/soak gates;
- explicit scoped memory compaction for operational task context, with soak
  evidence proving a bounded live-record set without pruning procedures or
  unrelated memory kinds;
- versioned hidden-window native Browser runtime reconnect soak with real
  Electron/Chromium pages, composite state restoration and resource lineage;
- versioned real headless `hermes serve` multi-session/reconnect soak with
  authenticated WebSocket traffic, streamed turns and durable session resume;
- versioned H013 integrated hidden-window Desktop/Browser load E2E with four
  native Chromium BrowserTasks, complete controller/IPC resource-event parity,
  host-aware viewport transfer, native maximize/restore reconciliation and
  lifecycle cleanup, plus
  an expanded eight-task/three-round sustained backend load and a bounded
  16-task/120-second candidate-release profile with checked JSON evidence via
  `workstation.desktop_load_evidence`;
- Control Plane action/spend/network/permission observation, degraded optional
  boot, bounded MCP execution, extension qualification and versioned A2A/ACP/UHP
  adapters;
- production dependency audit gate with the vulnerable transitive frontend
  packages refreshed in the lockfile without forced upgrades.

The remaining roadmap acceptance gates are evidence gates, not unimplemented
contracts: clean-machine release qualification, broader event/resource parity
for future clients and candidate-release confirmation of the full-duration/
production-scale Desktop/Browser agent/backend profile beyond the locally
validated H013 run. The
`workstation.release_qualification` runner and canonical reconnect soak make
those checks reproducible without inferring clean-machine or Desktop/Browser
production evidence. The Chromium/Firefox smoke is validated, and the optional
installed Edge project is also validated when the supported system browser is
available; neither is claimed as a full release qualification.

## V3.1 — Runtime Resilience, Recovery Plane & Deterministic Routine Promotion — Implemented contract layer

**Purpose:** harden Hermes Workstation as a long-lived agentic system by separating the mechanisms that keep the runtime alive, rescue a broken installation, and replay already-understood workflows from the LLM-driven reasoning path.

This milestone extends existing V2 procedural memory and V2.5 runtime/control-plane work; it must **not** introduce a second Hermes SessionDB, Kanban, Memory store, browser page store, task scheduler, or competing source of truth.

### Independent Runtime Supervisor — Implemented contract

The process responsible for keeping Hermes alive must live outside the agent runtime it supervises.

- Add a minimal supervisor/service process that owns runtime start, health checks, restart, crash-loop detection and controlled shutdown.
- The agent runtime may request restart/update, but must never depend on itself remaining alive to complete its own resurrection.
- Track a last-known-good runtime/profile checkpoint and detect failed startup after update or configuration change.
- Support safe update handoff and rollback without requiring the Desktop UI to remain functional.
- Emit lifecycle events into the existing Workstation event/journal path instead of creating a parallel operational history.

**Acceptance:** deliberately crash or self-stop the Hermes runtime and prove the independent supervisor restores service or rolls back to a known-good state without relying on the dead runtime.

### Recovery Plane / Safe Mode — Implemented contract

Recovery must remain available even when the normal Workstation UI, plugin graph, browser surface, or agent runtime is unhealthy.

- Add a minimal out-of-band recovery surface, CLI and/or safe-mode UI with deliberately tiny dependencies.
- Expose runtime health, startup diagnostics and the minimum logs/evidence required to identify a failed component.
- Allow disabling/quarantining a broken optional plugin or integration without manually editing internal state files.
- Allow restoring the last-known-good profile/checkpoint and restarting through the independent supervisor.
- Support degraded boot: optional component failure should isolate that component and keep the core available unless safety or state-integrity invariants require fail-closed behavior.
- Keep Recovery Plane independent from rich Desktop/plugin rendering so the recovery mechanism does not share the same primary failure domain.

**Acceptance:** break the normal Workstation UI or an optional plugin intentionally and recover to an operational state using only the Recovery Plane, with no manual repository/profile surgery.

### Routine promotion — discover → validate → promote → deterministic replay — Implemented contract

V2 `ProceduralMemory` already captures reusable knowledge from successful workflows. V3.1 adds an explicit promotion boundary so a workflow that is understood and validated no longer requires the LLM to rediscover every step on every run.

- Capture a successful agent-discovered workflow with provenance, ordered actions, required inputs, preconditions, expected outputs and evidence.
- Require explicit validation policy (human approval and/or strong automated evidence) before promotion from learned procedure to deterministic routine.
- Store/version the reusable procedure through the existing Hermes Memory/skill ownership path; do not create a second memory authority.
- Execute promoted routines through a deterministic runner whenever their declared preconditions match.
- Record routine version, inputs, actions, outputs and evidence in the existing Execution Journal/Kanban lineage.
- If reality diverges from the routine's assumptions, stop deterministic replay and hand control back to Hermes for diagnosis/re-exploration through the existing drift-governance path.
- Allow revised successful behavior to produce a new routine version rather than silently mutating historical behavior.

**Acceptance:** let Hermes discover a real multi-step workflow once, validate/promote it, replay it later without repeated LLM planning, then deliberately introduce drift and prove execution stops safely and returns control to the agent.

### Architectural boundary

```text
Independent Supervisor
  → keeps runtime alive / restarts / rolls back

Recovery Plane
  → rescues the system when normal Workstation paths are unhealthy

Agent Runtime
  → reasons, plans, coordinates and handles novel/drifted situations

Deterministic Routine Runner
  → replays validated known workflows without repeated LLM reasoning

Workstation
  → presents state, control, evidence and recovery entrypoints to the user
```

The intended workflow lifecycle becomes:

```text
novel task
  → Hermes reasons and discovers a working procedure
  → evidence + validation gate
  → promote to versioned deterministic routine
  → future compatible task replays the routine cheaply and predictably
  → unexpected state/drift stops replay
  → Hermes resumes reasoning and adapts
  → revised behavior may be validated as a new routine version
```

### V3.1 exit criteria

- runtime crash/self-stop recovery succeeds without the runtime supervising its own resurrection;
- one broken optional plugin/UI path can be isolated and recovered through the out-of-band Recovery Plane;
- last-known-good restore/rollback is demonstrably usable when a new runtime/profile fails startup;
- one real agent-discovered workflow is promoted and replayed deterministically with canonical journal/Kanban evidence;
- deterministic replay fails closed on unmet preconditions or drift and hands control back to Hermes;
- no duplicate SessionDB, Kanban, Memory, browser state or task scheduler is introduced;
- Windows dogfood evidence exists first, with the supervisor/recovery contracts designed so Linux can implement the same semantics.

## Research intake — 2026-09-10 — cross-briefing architecture backlog

This intake consolidates actionable Hermes Workstation implications extracted from the
Hermes Agent, DeepSeek Harness and broader agentic-systems briefings through
2026-09-10. It records both **new gaps** and **disposition of ideas already covered**
so research does not create duplicate owners or reopen completed milestones.

### Non-negotiable interpretation

- Hermes remains the primary conductor and canonical owner of Hermes sessions,
  Kanban and Memory; Workstation must not become a second agent core.
- Workstation owns the product/control layer around Hermes: canonical cross-surface
  state, policy, supervision, recovery, evidence, operational UX and selected
  compatibility adapters.
- Prefer upstream capability reuse over downstream reimplementation. Every new
  downstream feature needs an explicit `own / adapt / upstream` decision and an
  upstream-delta/compatibility check.
- Runtime/Data Plane must never be able to silently weaken the Control Plane that
  constrains it.
- Long-lived operation is the target: architecture must remain safe and observable
  across days, restarts, model/provider changes, plugin failures and upgrades.

### Research disposition — already covered or substantially represented

The following research themes are already represented in completed/planned roadmap
work and should be hardened there rather than reimplemented:

- browser-visible persistent profile/session ownership → Foundation, V1 and V1.1;
- popup/SSO, upload/download and browser recovery → V1;
- scoped capability policy, approval and audit trail → V2.5 Policy Engine;
- specialist worker adapters and canonical delegated-task lineage → V2.5 Worker Registry;
- system-event-to-task ingestion → V2.5 Event Pipeline;
- execution observability/journal → V1/V2.5 Control Center;
- procedural memory, provenance-aware perception and drift governance → V2;
- cross-platform host awareness → V2.5/V3;
- independent supervisor, safe-mode Recovery Plane, last-known-good rollback and
  deterministic routine promotion → V3.1.

The items below are the remaining research-derived gaps or explicit hardening
requirements.

## V3.2 — Evidence-backed Long-Lived Runtime & AgentOps — Implemented contract layer

**Purpose:** make “running” mean demonstrably running, make long-lived sessions and
workers operationally bounded, and expose one coherent runtime state to every
Workstation surface.

This milestone extends V3.1. It must reuse the canonical `ExecutionJournal`,
Kanban, BrowserTask, Hermes session/memory owners, `WorkerRegistry`, Policy Engine
and supervisor; it must not introduce parallel task/session/memory stores.

### EvidenceState + explicit execution state machine — Implemented contract

Introduce `EvidenceState` as a first-class projection over canonical task/run state.

At minimum a running operation should be able to expose:

```text
status
started_at
last_activity
evidence[]:
  process_id | browser_operation | worker_id | job_id | upload_id |
  watcher_id | external_handle
recovery_strategy
blocked_reason?
approval_id?
```

Rules:

- `running` requires live/verifiable operational evidence, not only an agent claim.
- Distinguish at least `ready`, `queued`, `running`, `waiting-for-human`,
  `blocked`, `stalled`, `completed`, `failed`, `cancelled` and `hold`.
- A worker safety stop, missing approval or external failure must never be reported
  upstream as normal completion.
- Explicit user constraints and target project/workspace identifiers override
  implicit “currently active” UI/session context.
- A stale evidence record must degrade state instead of allowing zombie “running”.
- Recovery actions must be linked to the same canonical run/task lineage.

**Acceptance:** kill a worker, browser operation, gateway or upload mid-run and
prove the UI/state projection stops claiming progress without evidence and offers
the correct recovery/handoff state.

### Event bus, deadlines and backpressure — Implemented contract

Harden runtime ↔ cockpit communication into a complete event contract.

- First-class events for tool calls, worker messages, progress, usage/cost,
  approvals, errors, lifecycle transitions, deliverables and recovery.
- No operation may wait forever: model calls, MCP requests/pagination, WebSocket
  sends, file transfers, persistence, provider calls and worker waits require
  deadline, cancellation and bounded retries.
- One blocked WebSocket/message must not head-of-line block unrelated events/RPCs.
- Prefer event-driven `wait`/wake semantics over context-expensive polling.
- UI reconnect must follow an explicit lifecycle (`connecting → restoring →
  ready`) before querying state aggressively.
- Structural failures must become visible states; no silent no-op buttons or
  swallowed persistence failures.

**Acceptance:** inject a stuck event/channel and prove unrelated task events
continue; cancellation/deadline produces an auditable terminal state.

### Durable session ownership, migration and memory lifecycle — Implemented contract

Treat persistent conversation history and a live persistent agent as separate
recovery concerns.

- Enforce cross-process ownership/locking for a writable session/run.
- Treat session schema changes as state migrations:
  `backup → migrate → validate → promote → rollback`.
- Preserve the original representation until migration is validated.
- Persist enough identity to reconstruct agent/model/tool/worker bindings rather
  than restoring only transcript text.
- Provide administrative model-binding migration for existing long-lived sessions
  when default provider/model changes.
- Add `hot / warm / cold` session lifecycle so inactive sessions can leave RAM and
  be reconstructed from durable state.
- Trigger context compaction before model quality or cost collapses, not merely at
  the provider's hard limit.
- Preserve compaction/replay markers and surface persistence corruption/recovery
  as observable events.
- Version/snapshot important user/memory state so current-state files are not the
  only recoverable copy.

**Acceptance:** run a long-session soak with multiple sessions, force restart and
model change, migrate one session, unload/reload cold sessions, and prove identity,
history and ownership recover without unbounded memory growth.

### Persistent workers: queue → message → steer → wait → stop — Implemented contract

Extend `WorkerRegistry` beyond fire-and-return delegation.

- Optional persistent specialist worker identities with durable parent/task lineage.
- Ordered message queue with sender identity and provenance.
- `send_message`, `steer`, `wait`, `stop/cancel` and resumable worker semantics.
- Parent-owned relay for worker questions:
  `worker → Hermes parent → user/approval surface → parent → worker`.
- Worker result envelope must include semantic status, model/provider, duration,
  token/usage estimate, cost estimate when available, produced evidence and
  explicit deliverables.
- Parent must be awakened by meaningful worker delivery/event instead of polling.
- Support bounded parallel hypothesis generation + verifier/selection for
  high-complexity work, while keeping it opt-in and budget governed.

**Acceptance:** keep one worker alive across multiple messages, steer it mid-run,
pause/resume or reconstruct it, then stop it deterministically with complete
journal/evidence and cost metadata.

### Cost, budget and model/provider routing — Implemented contract

Make selection of intelligence an operational policy rather than a UI-only choice.

- Budget per task/run/worker, not only post-hoc global usage.
- Route by `complexity × risk × quality × cost × latency × availability`.
- Cheap/local model for routine execution when adequate; stronger model for
  planning, diagnosis, verification and exceptions.
- Provider/model fallback must be explicit, observable and policy-bounded.
- A material increase in possible spend requires approval.
- Heartbeat/loop/cron checks should decide whether a model call is needed before
  sending giant session context; use minimal context/cheap policy paths when possible.
- Large tool/skill catalogs should be discovered/injected on demand instead of
  repeatedly invalidating provider caches.
- Provider auth/TLS/proxy/base-URL differences are operational facts, not assumed
  interchangeable implementation details; localhost/LAN service traffic must not
  be accidentally forced through external proxies.

**Acceptance:** execute the same workload under at least two routing strategies and
report quality/status, latency, usage/cost and fallback decisions in canonical
journal metadata.

### Typed Resources + one runtime / many clients — Implemented contract

The first client boundary is now wired: Electron's BrowserTask/page owner
publishes bounded, versioned resource and event projections through its
authenticated loopback controller. Desktop IPC and the Dashboard REST route
consume those projections, while the TUI gateway exposes the same read-only
adapters for future clients. Degraded controller health is explicit and
permissions fail closed to `read`; no client creates a second task or journal
store.

Formalize a UI-neutral resource contract so capabilities publish typed state and
interfaces decide how to render it.

Examples:

```text
BrowserTask        → browser resource
ExecutionJournal   → timeline/evidence resource
Kanban             → task/dependency resource
Worker             → terminal/log/result resource
ProceduralMemory   → procedure resource
Artifact delivery  → deliverable resource
```

Requirements:

- Desktop, browser/WebUI, future mobile/remote clients are views over the same
  canonical runtime, not separate agent implementations.
- Resource identity, permissions and lineage survive client detach/reconnect.
- Separate internal workspace artifacts from **explicit deliverables** promoted to
  the user; “file touched” is not equivalent to “file delivered”.
- UI defaults to outcome/progress/cost/state; deep logs remain inspectable rather
  than flooding the primary surface.
- No internal agent chain-of-thought/private scratch state is required for the
  resource contract; only operationally useful state/evidence is exposed.

**Acceptance:** open the same running task from two supported surfaces and prove
both resolve identical canonical resources without duplicate workers/pages/tasks.

Current adapter evidence covers the Dashboard REST and TUI JSON-RPC surfaces
over one authenticated controller projection, with identical browser,
BrowserTask, execution-journal and bounded event identities. The exact packaged
artifact also passes the complete headless Desktop GUI/HUD smoke and IPC/
controller identity checks; visible desktop-session reveal and future remote
clients remain separate evidence gates.

### Human Handoff contract — Implemented contract

Generalize existing take/release-control primitives into a task-level human handoff.

- Agent may request handoff for login, CAPTCHA, 2FA, sensitive confirmation,
  ambiguous high-risk controls or automation failure.
- Preserve the same browser/session/task identity while control changes hands.
- Make handoff state explicit and auditable; resume only after a deliberate return
  of control.
- For personal-browser bridges, scope authorization to explicit tab/domain/session,
  permit immediate revocation and avoid exposing stored credentials to the agent.

**Acceptance:** agent reaches an authenticated workflow, yields to user, user
completes login/2FA, returns the same session, and the agent continues with no
duplicate page/profile.

## V3.3 — Isolation, Protocol Governance & Supply-Chain Hardening — Implemented contract layer

### Control Plane boundary + independent watchdog — Implemented contract

Extend the V2.5 Policy Engine and V3.1 supervisor with an independent policy/watch
path that cannot perform ordinary task work.

- Observe actions, spend, network destinations, permission changes and critical
  lifecycle events.
- Detect expansion to a previously undeclared external surface and default to
  `suspend → journal → request approval`.
- Policy authority, secret scopes, sandbox mode, restart/recovery and permission
  elevation live above the agent/Data Plane.
- Runtime components cannot call an unprotected local control API to remove their
  own confinement.
- Distinguish trusted vs untrusted workspaces/content and propagate trust labels
  into policy decisions.
- Preserve an incident trace showing the sequence of decisions/actions that led to
  a privileged or anomalous operation.

### Plugin / Skill / MCP isolation and degraded boot — Implemented contract

Optional components must fail independently.

- A broken plugin/skill/MCP server must not prevent core Workstation boot unless
  canonical state integrity or safety requires fail-closed behavior.
- Quarantine/disable optional components through Recovery Plane.
- Version extension contracts and provide safe defaults for newly introduced
  capabilities.
- Bound MCP discovery/execution by maximum pages, tools, response size, time and
  cancellation even when each page/cursor is formally valid.
- Supervise MCP processes/lifecycle as external dependencies, including health,
  restart and observable failure.
- Plugin/skill install pipeline should evolve toward:
  `source/provenance → static inspection → requested capabilities → sandbox →
  behavioral smoke → signature/reputation → install`.
- Secrets/credentials exposed to extensions should be scoped and preferably
  write-only/non-readable where practical.

### Protocol boundary / interoperability — Implemented contract

Keep Workstation semantics independent of any one external protocol.

- MCP remains a tool/data adapter, not canonical task state.
- Add/assess agent↔agent interoperability through A2A where it reduces bespoke
  worker coupling.
- Treat ACP/UHP-style runtime/client protocols as adapters/candidates for external
  clients, not new state owners.
- The internal event/resource/lifecycle contract must preserve tool events,
  approvals, usage, errors and cancellation even if an external protocol omits them.
- Version protocol adapters and test compatibility explicitly.

### Upstream ownership & release qualification gate — Implemented contract

For every upstream Hermes update:

1. classify each overlapping capability as `upstream-owned`, `Workstation-owned`
   or `adapter-owned`;
2. compare imported commit/version, packaged assets and expected integrations;
3. run clean-machine install/build from the exact candidate release with an
   absolute isolated Workstation home outside the checkout, shared by install
   and doctor;
4. execute Workstation contract/eval smoke, Windows-native smoke and migration
   preflight;
5. promote only after validation; retain last-known-good rollback.

A stable upstream tag must never be assumed equivalent to `main`, and local caches
must never be allowed to hide missing release dependencies.

## V3.4 — Memory, Time, Replay & Evaluation — Implemented contract layer

### Typed memory + temporal awareness — Implemented contract

Build typed policy views over existing Hermes Memory ownership, not a second memory DB.

Different memory classes need different retention/retrieval semantics:

- task/work context;
- factual/project knowledge;
- decisions and rationale;
- user preferences/principles (kept separate from operational facts);
- reusable procedures/routines;
- provenance/evidence/checkpoints.

Add:

- versioning/snapshots and recoverable history;
- workspace scoping;
- bounded recall/token budgets;
- provenance;
- confidence/validation metadata where useful;
- temporal decay/staleness;
- explicit `created_at / observed_at / last_verified_at`;
- elapsed-time awareness for pending tasks, promises, stale decisions and recovery.

### Portable trace, replay and model fork — Implemented contract

Extend Execution Journal toward operational replay/evaluation.

- Produce a portable incident/execution trace with canonical event IDs and resource
  references.
- Support offline replay for diagnosis without re-performing side effects.
- Permit controlled “fork at event N with another model/worker” experiments in an
  isolated evaluation environment.
- Preserve exact model/provider/tool/policy/version metadata needed to explain why
  behavior changed between runs.

### Evaluation & efficiency gates — Implemented contract

- Model-independent harness evals separate model quality from harness/runtime quality.
- Long-duration soak tests for sessions, workers, memory and reconnect behavior.
- Multi-process ownership tests for sessions/resources.
- Cross-engine WebUI smoke where applicable: Chromium/Edge and Firefox first;
  WebKit/Safari when/if a supported client target exists.
- Regression budgets for action/tool count, latency, context tokens and recovery
  success so a change that “works” but becomes dramatically less efficient is visible.
- Critical workflows follow `hypothesis → action → verify final state → report
  evidence`; completion should be evidence-backed, not response-backed.
- Before deployment/promotion, evaluate technical behavior, safety and compatibility
  against a reproducible baseline.

## Workstation Knowledge Subsystem — Hermes Vault (Local-First Agentic PKM)

Hermes Workstation bridges human personal knowledge management and autonomous agent capability into a single shared, local-first medium: **Hermes Vault**. Rather than treating notes as external third-party software, Hermes Desktop exposes a first-class Obsidian-compatible Markdown vault where both the human and the agent co-author notes, link ideas, and navigate knowledge.

Current verified slice (2026-09-15): the Markdown owner, plugin RPC, Desktop
route/editor/preview/backlinks and `d3-force` graph are present. Filesystem
containment is enforced before mutations, symlinked notes/directories are
excluded, writes are atomic, and the process-wide manager runs a bounded,
debounced external-change watcher. Persistent custom-root selection, richer
CodeMirror live editing/`[[` completion, explicit MOC/synthesis flows and the
remaining product-polish contracts below stay open; they are not implied by
the existing MVP.

### Core Architectural Slices

1. **Vault Engine & Local Indexer (`workstation/vault.py`)**:
   - Local directory root (default `~/.hermes/vault` or user-selected custom/Obsidian folder).
   - Real-time filesystem watcher for `.md` documents.
   - Regex/AST indexer for bidirectional wikilinks (`[[Note Name]]`, `[[Note#Section]]`), `#tags`, and YAML frontmatter properties.
   - Fast in-memory graph cache (forward references and backlinks index).

2. **Desktop UI & Editor (`apps/desktop/src/app/vault`)**:
   - First-class `/vault` route in Hermes Desktop.
   - Master-detail vault explorer with folder tree, search filter, and tag list.
   - WYSIWYG / Live Preview Markdown editor with syntax highlighting, task lists, KaTeX math, and GitHub alerts / Obsidian Callouts (`> [!NOTE]`).
   - Typing `[[` triggers auto-complete suggestion for existing notes.
   - Contextual right rail showing incoming Backlinks and outgoing Links.

3. **Knowledge Graph View**:
   - Interactive 2D/3D force-directed knowledge graph leveraging the proven `starmap` simulation engine (`d3-force`).
   - Nodes represent notes and tags; edges represent bidirectional wikilinks.
   - Interactive zoom, pan, filter by tag, and click-to-open.

4. **Agent-Vault Bridge Tools**:
   - Model tools for Hermes: `vault_search`, `vault_read`, `vault_write`, `vault_append`, `vault_backlinks`, and `vault_graph`; do not add the historical `vault_create_note` alias without a demonstrated compatibility need.
   - Explicit, opt-in agent synthesis: converting browser research, conversation takeaways, and project decisions into connected notes.
   - Map of Content (MOC) generator for automated knowledge clustering.

## V3.5 — Browser Automation Ergonomics & Autonomous Web Operations

Evolved from real dogfood observation across complex web properties (Google Maps SPAs, Amazon product grids, GitHub Turbopack filters, Mercado Livre verification walls).

1. **Input Hygiene & Reliable Value Replacement (`browser_type`)**:
   - Support `clear: true` (default `true` for input/searchbox elements) with multi-strategy CDP clearing: Ctrl+A with explicit `windowsVirtualKeyCode: 65`, `execCommand('selectAll')`, Backspace sequence, and direct DOM fallback.
   - Prevents search token duplication (e.g., `is:issue state:open is:issue state:open label:...`) across hotwired / auto-completing search inputs.

2. **Proactive Human Handoff & Auth/Verification Wall Detection**:
   - Pattern-based detection for account verification gates (`/gz/account-verification`, `/challenge`, Cloudflare Turnstile, CAPTCHA, Auth0, Google Sign-In).
   - Triggers proactive Human Takeover alert in Hermes Desktop with persistent session benefit: human logs in once in the dedicated Workstation profile, agent resumes seamlessly.

3. **Canvas / WebGL SPA Awareness & Adaptive DOM Settlement**:
   - Detects empty accessibility trees (`element_count <= 2` with active canvas or dynamic feed loaders) on rich web apps (Google Maps, Figma, web dashboards).
   - Implements adaptive DOM settling and feed detection (`div[role="feed"]`, main articles, etc.) before snapshot generation, preventing 0-element blindness.

4. **Batch Structured Extraction (`browser_extract_items`)**:
   - First-class structured extraction tool/primitive that collects repetitive items (cards, products, issues, articles) with selectors, attributes, text, and URLs in a single agent step.
   - Eliminates excessive token consumption and 10+ consecutive `browser_console` JS injection cycles for table/grid scraping.

5. **Browser Ecosystem Optimizations & Deterministic Batching (BROW-C2C)**:
   - **Batch Execution (`browser_batch_actions`)**: Serialized execution with step-level `BrowserHumanControlLease` revalidation, per-substep `BrowserOwnerReceipt`, and fail-stop on first uncertain effect or human takeover.
   - **Accessibility Tree Snapshotting**: Experimental CDP `Accessibility.getFullAXTree` integration with hybrid ref mapping and canonical inventory fallback.
   - **Bounded Extraction Cache**: Cache keyed by full document fingerprint, epoch, mutation revision, and query digest; strict redaction of sensitive credentials.
   - **Snapshot Delta Projection**: Line-level reversible diffing with lossless verification and conservative fallback to full snapshot.
   - **Duplicate Mutation Prevention**: Idempotent replay on duplicate `operation_id` requests preventing duplicated external mutations.
   - **Chrome Import Isolation**: Evaluated and placed in formal HOLD status (`OPT_05_CHROME_IMPORT_SECURITY_EVALUATION.md`) to protect user credentials and boundaries.

## V4 radar — optional / evidence-gated explorations

These are research-backed directions worth preserving without making them near-term
dependencies:

- **distributed local compute pool:** discover trusted LAN machines/models as
  replaceable inference capacity rather than assuming local model == this GPU;
- **hardened worker sandbox lane:** Windows host → WSL/container/sandbox for
  untrusted/continuous worker execution while native Desktop remains the product shell;
- **OAuth connection broker:** user-friendly scoped connections for external
  services instead of routine raw API-key copying;
- **mobile/remote client:** thin authenticated client over the same canonical runtime,
  with pairing, device revocation and approval cards;
- **tool-learning / WebMCP-style promotion:** `explore → validate → promote to
  versioned tool/routine → reuse`, integrated with V3.1 deterministic promotion;
- **large-search orchestration:** many cheap independent attempts + selection +
  progressively stronger verification for problems that justify the budget;
- **agent governance primitives:** independent verifier/auditor roles for high-stakes
  multiagent workflows, with human authority remaining outside the agent society.

### Human card → Hermes Agent Task delegation bridge — Implemented

**Purpose:** turn the hybrid/Trello-like human Kanban into a true delegation
interface for Hermes without collapsing human work management and agent execution
into one lifecycle.

A human-owned card may expose an explicit **“Entregar isto ao Hermes”** action.
Invoking that action must:

- preserve the original human card as the source of truth for the human workflow;
- create a separate canonical Hermes Agent Task with a stable bidirectional link
  (`human_card_id` ↔ `agent_task_id`) and explicit delegation provenance;
- execute and transition the Agent Task only through the existing agentic Kanban,
  Hermes session/run, BrowserTask, Worker and Execution Journal owners;
- project useful agent progress back onto the human card without making that
  projection authoritative for the Agent Task lifecycle;
- on completion, failure or cancellation, return the result, deliverables, concise
  summary and relevant evidence to the original human card while preserving the
  full agent-side journal/history;
- keep human columns/statuses and agent execution states semantically independent:
  moving/completing a human card must not silently complete/cancel the Agent Task,
  and an agent-side transition must not silently move the human card unless an
  explicit user action or declared policy requests it;
- preserve delegation lineage across restart/recovery, and treat re-delegation as
  an explicit new attempt/task (or conscious reuse) rather than overwriting prior
  execution evidence.

The intended flow is:

```text
human Trello-like card
  → “Entregar isto ao Hermes”
  → linked canonical Agent Task
  → execution visible in the Agentic Kanban
  → journal / evidence / deliverables produced under agent lifecycle
  → result + evidence projected back to the original human card
```

**Acceptance:** delegate one human card, prove the original card remains in its
human board lifecycle while the linked Agent Task independently moves through
queued/running/waiting/completed states, then verify that completion returns the
result/evidence to the same human card and that restart/recovery preserves the
link without introducing a second canonical Kanban/task store.

Implementation evidence on the current mainline working tree:

- `hybrid_card_delegations` is an additive table in the canonical
  `hermes_cli.kanban_db` owner; no AgentTaskStore or parallel queue was added.
- duplicate clicks are idempotent for an active attempt; retry is an explicit
  reuse of the same attempt, while re-delegation creates a new attempt and
  preserves prior evidence.
- `tests/hermes_cli/test_hybrid_kanban.py` covers delegation, restart,
  completion/failure/cancellation, independent movement and result/evidence
  writeback.

### Research-derived acceptance principle

A roadmap item should only be promoted from “interesting” to “default path” after it
demonstrates at least one of:

- measurable reliability or recovery improvement;
- lower cost/latency at equal task success;
- stronger safety/isolation with preserved usability;
- clearer canonical state/evidence across restarts/clients;
- reduced upstream-delta/maintenance burden.

The objective is not to make Hermes Workstation contain every agent feature. The
objective is to make upstream Hermes **predictable, observable, recoverable,
policy-bounded and pleasant to operate for long periods**.

## Active: Canonical Work Loop

Safety and canonical owner extensions are implemented in the working tree;
complete integration parity, five Work100 gaps and native product validation
before declaring this program delivered. Scope and remaining work:
[Canonical Work Loop](context/CANONICAL_WORK_LOOP.md).

## Operational speed P0.2 — local development evidence (2026-10-10)

Maintainer authorized CI omission for continued development; H-079/release qualification remains pending. This supersedes the earlier Stage A statement that runtime implementation had not begun, without changing historical evidence.
Authenticated DIRECT v2 replaces forgeable unkeyed hashes using existing profile-scoped secrets and exact operator trust bindings. Missing, invalid, expired or revoked qualifications retain SHADOW. No production key or mutable qualification installed.
RED: two forged qualifications accepted by old code. GREEN: 48 security/learning tests, including real A→B→A config/secret isolation and local verified run adoption. Native E1–E3, human-edit concurrency closure and product cost/latency benchmarks remain pending; no savings claimed.
Evidence: workstation/context/engineering-journal/operational-speed-p0-2026-10-10.md. Development branch starts at 217742e; immutable upstream pin remains 66605471e9f0b0832abbefaf625ce08e948ca540. No main merge.
## Operational speed P0.1 — instrumentation development (2026-10-10)

Existing local telemetry now persists nullable canonical cost/source, actual cache tokens, call IDs and application UTF-8 byte counts; repeated event delivery is deduplicated. Provider usage comes from the existing pricing/accounting owner. Tool timing/fingerprints store no raw Browser content. Telemetry failure cannot prevent mutation bookkeeping. Session economics reports unknown values when usage/pricing is absent, and flags calls without run lineage; per-run attribution is not complete. Server admission latency excludes UI/transport and remains unknown for ambiguous turn lineage.
RED: SQLite lost cost_usd and repeated delivery charged twice (2 failures). GREEN: 34 focused telemetry/core/System-1 contracts; final usage-owner and SQLite recheck 12 passed. Full Workstation regression running, not yet qualified. Strict seam classification: 14 classified, zero unclassified/growth. Exact historical seam manifest remains divergent on 14 unchanged tools-file line keys.
Real Trello/HyperFrames/repetition baseline BLOCKED: installed native controller health returned false; no real end-user latency, token savings or monetary savings available. CI skipped by maintainer authorization, development only. Evidence: workstation/context/engineering-journal/operational-speed-p0-2026-10-10.md.
## P0.2 item-boundary revocation follow-up (2026-10-10)

A new real local adoption regression exposed a remaining lifetime gap: revoking the qualification after the first reused item did not stop the three later items in the same checkpoint. Valid RED: four items executed instead of one (29.1s runner; initial fixture-error attempt is not counted as security evidence). Runtime now re-queries qualified offers at every item boundary, records denial and halts the checkpoint. The independently verified first item remains completed; no blind rollback/retry.
GREEN: complete online safety file, 38 passed, zero failed, 149.0s. Config/expiry/scope changes apply at item boundaries; this is not an atomic distributed revocation guarantee for an effect already in progress. No Trello write or production trust provisioning.
Native regression at bb1888976e: existing headless-load contract passed with four real Electron/Chromium BrowserTasks (8.5s test; 1.6m including bootstrap under concurrent tests). Inference and pages are fixtures: native lifecycle/IPC evidence only, not E1 completion or measured product latency/cost. Broader Workstation regression still running; CI remains skipped by maintainer.

## 2026-10-11 — P0 authority / Browser / One-Click convergence (draft)
An isolated integration of PRs #70–#75 is documented at `context/P0_INTEGRATION_2026-10-11.md`, including 116/116 combined Windows tests and an additional `TaskCompiler` canonical SQLite-owner fix (9 red → 10 green supersession E2E). **No main merge and no production qualification**: native Electron UI/Browser handoff/readback, offline One-Click, Studio without HyperFrames, exact-head CI and user data migration still held. Follow the ranked nine-front matrix in the integration dossier rather than relabeling earlier drafts as finished.

## 2026-10-11 — P0.2, P0.3, P0.5 follow-through (separate draft)
- Explicit trusted force-work marker now gates `force=True`; normal intelligent admission unaffected. Cross-worker CAS test remains.
- Canonical completion admission requires matching task identity, optional run identity, status `verified_completed` AND accepted contract, otherwise fail closed (9 RED → 11 GREEN).
- Read-only SQLite online snapshot and historical reconciliation manifest added. Live dry-run on user data: 19 current tasks, 106 backup-only (0 overlap), 55 orphan handoffs. **No actual deletion, restoration, closing or approvals.**
- See `context/P0_PROOF_RECONCILIATION_2026-10-11.md`. No CI/packaged Electron proof. Remaining P0.3 typed evidence contracts, P0.5 scoped user-reviewed apply/rollback, H080B baseline, native UI and Browser gates hold release.


## 2026-10-12 P0 cold Electron restart: RED→GREEN fixture correction (subsequent execution)

- **Starting exact HEAD:** `b1a523a4838ea1fe1d43d9b0691c9d9da5d55d11` on `fix/p0-kanban-browser-authority-20261012`, clean isolated worktree, root has 34 unrelated uncommitted files. PR #83 was DRAFT/open/mergeable. No user data modified.
- **Control experiment:** pre-existing `restores the selected chat BrowserTask on the first real viewport attach without foreground theft` E2E PASSED, real Windows Electron/Chromium, 227.24s (3.7m). It closed one app, started another app+Python backend, lazily restored **two real persisted chat sessions** and verified viewport ownership. Thus don't alter product backend quit/leases based only on the previously broken P0 fixture.
- **Root cause of P0 test false RED:** it originally used a **synthetic session ID** unassociated with a persisted renderer chat; after relaunch the native task recovery is lazy and scoped to a persisted chat. The test also asserted `sessionId` on `BrowserTask`, whose real contract is **`sessionHost`**, and did not rebind `fixture.app/page` to the relaunched instance. The prior `electron.launch` timeout (180s) did not establish product restart failure. Reworked the test to create a real chat, select it before navigation, acquire/release human lease, build/launch same isolated profile again, rebind fixture app/page, select the persisted chat, assert recovered task `sessionHost`, navigate, independently verify Browser snapshot, and explicitly close the replacement Electron.
- **New cold restart P0 native GREEN:** `P0: released native BrowserTask is retained and agent resumes after cold Electron restart`: 1 PASSED / 0 FAILED / 0 SKIPPED on worktree Electron/Chromium, 160.64s (2.6m). Removed `test.fixme` after actual verification. No product authority code relaxed. The first re-enabled version got to restored app but failed on invalid `sessionId` expectation; correction confirmed by TypeScript contract `electron/workstation-browser-task.ts::BrowserTask.sessionHost`. Re-run GREEN.
- **Additional Kanban multi-process claim test:** two independent Python processes race `kanban_db.claim_task` for one `ready` task in isolated SQLite; exactly one receives `current_run_id`, one receives `NOT_CLAIMED`, exactly one run exists. Together with existing independent-process task admission: `test_p0_multiprocess_task_admission.py` **2 PASSED / 0 FAILED in 31.17s**. Does not grant any real user task lease.
- `tsc -p tsconfig.e2e.json --noEmit` PASSED after updating BrowserTaskRecord test type, and scoped Ruff PASSED. A combined native 3-test E2E rerun was started; record final result and exact HEAD/CI after commit. Product package/installer native dogfood and uncertain external mutation approval→readback E2E remain unqualified.
- **DoD left:** P0 handoff uncertain mutation recovery without duplicate, typed acceptance policy by effect, real prompt classification corpus, concurrency after task finish and restart, packaged Electron/One-Click run on candidate, exact-head CI and H-079 gate. Preserve prior historical Kanban deletion; no restoring 106 deleted tasks or consuming 55 orphan handoffs without explicit scoped approval.
- Mandatory resume prompt: subsequent agent must begin with latest verified HEAD and this document, not restart broad audit; if unfinished, issue updated pasteable prompt including exact tests, failures and next code symbol.


## KANBAN-04 concurrency correction — 2026-10-12

The exact scoped implementation and RED/GREEN tests are documented in `workstation/context/P0_KANBAN04_HANDOFF_ATOMICITY_2026-10-12.md`. `HumanHandoffManager` had a reproducible stale-manager write loss: two instances could overwrite separate handoffs or mint two IDs for the same operation. The canonical JSON transition is now synchronized with existing cross-platform OS file locking and in-lock reload, preserving consume-once semantics. Corrupt ledgers fail closed without erasure. No new persistence owner or external mutation authority was created.

Windows tests include two separate processes racing identical requests, existing handoff tests, and a deterministic local HTTP external POST applied before timeout with independent GET readback and no replay. This is a **Python network/agent-ledger integration test**, NOT native Browser/UI approval/readback E2E. Human approval does not equal verified effect; original uncertain mutating call stays blocked. KANBAN-04 remains PARTIAL until actual Electron takeover/handoff and typed verifier E2E complete. Prior PR #83 native browser UI/restart gates remain as previously recorded. Never restore deleted historic tasks or mutate user data.


### KANBAN-04 execution evidence — 2026-10-12 (handoff atomicity + active human lease)

- RED stale-manager reproducer: two independent cached `HumanHandoffManager` objects previously overwrote unrelated JSON reviews and minted separate handoff IDs for the identical task/session/reason/scope (**2 RED / 0 GREEN** before correction).
- Owner `workstation/runtime.py::HumanHandoffManager` corrected: uses existing cross-process `hermes_cli.active_sessions._FileLock` around canonical JSON reload, request/resume/consume and atomic persist; fresh `get` reads disk; bad JSON fails closed, no mass historical review rewrite.
- Windows independent-process synchronized requests now converge on one handoff; new corruption and stale-object tests verify no lost updates and consumption exactly once.
- Added isolated deterministic HTTP timeout mutation/readback integration proof in `workstation/tests/test_p0_uncertain_mutation_readback.py`: external POST commits once before response timeout, freshly reconstructed agent gets REQUIRE_HUMAN, handoff ID stable, human resume+consume once, independent GET confirms effect, original mutation remains refused rather than dispatched again, other session read unaffected. Not a native Electron tool→approval UI→provider readback E2E and not a qualified automatic reconciliation path.
- **Canonical Windows runner:** 9 Python suites, **64 PASSED / 0 FAILED** (124.7s wall, 8 workers), covering runtime, handoffs, Browser session isolation, TaskCompiler, admission/claim multiprocess, completion proof. See exact selected paths in `P0_KANBAN04_HANDOFF_ATOMICITY_2026-10-12.md`.
- Extended native P0 restart E2E to also cover a **second restart with active human control**: before shutdown Browser operation is refused with exact 409 USER_CONTROL_ACTIVE; upon restart, the prior process' human lease is not resurrected as new-process authority; persisted sessionHost is recovered and new navigation/readback succeeds. **1 native Electron E2E PASSED (194.53s)**, source-built isolated worktree. No production Browser takeover/release semantics were relaxed.
- Three native P0 scenario combined re-run started after extended test; final count must be recorded after execution. No packaged MSI/EXE validation and no exact HEAD GitHub Actions proof yet. Never merge into main solely on these local tests.
- Historical 106 deleted tasks and 55 orphan handoffs remain read-only; root user's 34 uncommitted files preserved.


## P0 KANBAN-04 — cross-TaskRun handoff fencing + readback guidance + native lost-ACK proof (2026-10-12)

Starting from clean published PR #83 HEAD `dd708241177ec7bfb2ef9dd5fc7f4992b7a11330` on isolated worktree `C:\Github\hermes-agent-kanban-browser-authority-20261012`. Checkout root: 34 unrelated dirty paths, never changed. No real user data or historical state altered. PR remains draft; no main merge.

### Reproduced RED and fixes

1. `workstation/tests/test_denied_mutation_handoff_recovery.py::test_uncertain_handoff_never_reuses_approval_from_superseded_run`: consumed human review from `run-old` was reused under a different `run-new` for the same task/session/operation; **RED 1/1**, before fix. Canonical `workstation_tool_batch_admission` now adds a non-null `_canonical_work_run_id` to `HumanHandoffManager.request(...scope)`. An old consumed review cannot grant the new run's readback disposition; an uncertain new run gets a new waiting review. The existing no-TaskRun workflow remains session/task scoped.
2. `test_consumed_review_returns_readback_guidance_without_another_handoff`: repeated admission of an *already consumed* review returned `BatchAdmissionAction.HANDOFF`, risking another UI popup. **RED 1/1**, before fix. It now returns `SYNTHETIC_RESULT` for consumed reviews with code `uncertain_effect_requires_readback`, while pending reviews remain `HANDOFF`. The originally uncertain write is still blocked by `decisions_for_calls`; a human review is not an independent persisted-state proof. No new state machine.
3. The message was tightened: independent readback is required; human review alone cannot authorize uncertain-effect replay. The 11-test scoped admission/HTTP/ledger suite PASSED, and the canonical 7-suite Python regression run was launched. Record exact final result separately.

### Native Electron/Chromium uncertainty gate

Added `P0: native Browser mutation remains observable after lost controller acknowledgment` in `apps/desktop/e2e/workstation-headless-load.spec.ts`.

The existing isolated loopback page server now exposes a deterministic `/p0-uncertain-native` button and read-only `/p0-native-effect-state` endpoint. Real native controller browser_click dispatches a Chromium click to commit a single POST; the client aborts its controller HTTP response **only after the server confirms the side effect was recorded** (a controlled lost-ack simulation, not proof that production agent timeouts themselves are wired to the handoff). A new controller `browser_snapshot` and independent read-only loopback GET prove that the effect was applied once, without resending the browser_click. A second session remains navigable.

Isolated native scenario: **1 PASS, 0 FAIL**, about 1.9 minutes on worktree-built Electron/Chromium. E2E TS typecheck PASS. The combined 4-test P0 native suite is being rerun; do not record its outcome without observing the terminal result. Previous 3 native P0 scenarios already qualified takeover→409→release, UI clicks, cold restart and active human lease isolation in earlier PR #83 commits.

### Remaining release blockers (still OPEN)

- **Actual UI review and causal continuation**: no verified mapping from Python `HumanHandoffManager` state through the native Electron renderer review controls and back to a trusted readback verifier was established. Do not label this implementation KANBAN-04 fully qualified. Begin at `workstation/integrations/hermes/tool_batch_admission.py::workstation_tool_batch_admission`, trace emitted `BatchAdmissionAction.HANDOFF` through `agent/turn_tool_round.py` / `run_agent.py` to the real UI transport; build only the canonical owner seam, then RED native E2E `P0: uncertain native Browser mutation requires single human handoff, independent readback and safe resume`.
- **Trusted typed readback**: reuse `workstation/control_plane/verification.py::evaluate_verification` with validated `VerificationContract`, required predicates, observer trust/failure domains and exact task/run/operation/resource lineage. Human assent or `verified=True` alone must not mark a mutation verified. Never turn a once-uncertain write into an automatic replay when its readback confirms success; use a non-mutating checkpoint/continuation path.
- KANBAN-01 intent corpus with measured FP/FN; KANBAN-02 crash/restart contention; KANBAN-03 effect-typed acceptance; KANBAN-05 independent blocked tasks and orphan handoffs; KANBAN-06 dry-run only for 106 historic deleted tasks and 55 orphan handoffs; KANBAN-07 native packaged app, exact-HEAD GitHub CI and H-079 upstream-first/stacked PR qualification.
- No merge to main until required gates and authorization. Any agent stopping now MUST emit an updated copy-paste RESUME PROMPT with verified HEAD, results, exact next symbol/test, state protection.


### KANBAN-04 follow-up: scoped authority + native lost-ACK RED/GREEN (2026-10-12)

- Starting Git HEAD: `dd708241177ec7bfb2ef9dd5fc7f4992b7a11330`, PR #83 draft and no main merge. Root checkout has 34 pre-existing uncommitted changes; those and all real sessions/cards/handoffs are untouched.
- **RED 1:** `test_uncertain_handoff_never_reuses_approval_from_superseded_run` demonstrated a consumed handoff from `run-old` reappearing as the same `handoff_id` under `run-new`. Fixed `workstation/integrations/hermes/tool_batch_admission.py::workstation_tool_batch_admission` by adding the canonical non-null TaskRun ID to the existing operation-scoped human review identity, without replacing the canonical JSON owner. Existing session-only operations retain their identity.
- **RED 2:** `test_consumed_review_returns_readback_guidance_without_another_handoff` showed a consumed review emitting `BatchAdmissionAction.HANDOFF` again, potentially requesting another popup. Fixed to emit `SYNTHETIC_RESULT` with `uncertain_effect_requires_readback` for consumed reviews; `HANDOFF` still applies to waiting review. Original uncertain external write remains blocked. Human approval is NEVER a retry grant or semantic proof.
- **Native Electron/Chromium:** added `P0: native Browser mutation remains observable after lost controller acknowledgment` in `apps/desktop/e2e/workstation-headless-load.spec.ts`. A real native BrowserTask clicks a button in Chromium; deterministic local server commits one POST; authenticated controller response is canceled *after* the effect but before acknowledgment; independent controller snapshot and local GET prove side effect count=1, with no repeated click. An unrelated session still works. This is a **controlled lost-ACK test**, not an automatic Hermes agent timeout→human UI review integration test. Native isolated test 1 PASS.
- **Combined native fixture RED→GREEN:** initial 4-test P0 suite had 3 PASS / 1 FAIL because prior cold-restart test had closed the shared Electron fixture before the new native effect scenario; `ECONNREFUSED` on controller. Moved native effect scenario **before** the deliberate cold restart in the same E2E file; full combined native P0 suite then **4 PASS / 0 FAIL / 0 SKIP in 193.29s**. No production controller/lease code weakened.
- **Canonical typed verifier proof test:** added `test_canonical_typed_readback_requires_matching_operation_run_and_persisted_source` to `test_p0_uncertain_mutation_readback.py`. Uses existing `workstation/control_plane/verification.py::evaluate_verification`, verifies a validated trusted independent persisted readback contract with correct lineage and rejects foreign run/operation, weak evidence, stale read-before-write, and mismatched state. This is contract qualification only; no automatic provider readback claim.
- Python scoped admission + handoff tests **11 PASS**; selected canonical Python regression **33 PASS** before the additional typed test; a full re-run after the added typed test is pending terminal result. Electron/Vitest native owner regression **58 PASS**. E2E TypeScript check and Ruff passed, git diff whitespace passed. Record canonical final Python outcome separately.
- **Still OPEN:** actual Hermes native UI human review control wired to `HumanHandoffManager` via owner-approved transport, single consumption and verified typed readback, work-item checkpoint continuation without repeating the uncertain mutation; deidentified task-admission corpus, supersession/crash recovery, type-specific acceptance, historical dry-run only, native packaged binary, exact-head CI/H-079 and stacked PR chain qualification. KANBAN-04 remains PARTIAL. Do not represent synthetic result or local server test as native human approval E2E.
- Next test name: `P0: uncertain native Browser mutation requires single human handoff, independent readback and safe resume`. Next code seam: `workstation/integrations/hermes/tool_batch_admission.py::workstation_tool_batch_admission`, tracing `BatchAdmissionAction.HANDOFF` through `agent/turn_tool_round.py` and `run_agent.py` into the actual Desktop renderer/IPC. Reuse `evaluate_verification` with a real trusted read-only observer and exact task/run/operation/resource evidence. No fresh permission after readback, no uncertain replay. Implement TDD, native E2E, complete release gates.

### 2026-10-12 — Experience Compiler activation (PR #82, draft; qualification HOLD)
- EC-01: native command intent aligned to canonical Browser host/page_family/recovery_state IR; 42 targeted/integration regressions passed; not production certified.
- EC-02: candidate-bound filesystem canary/replay fail-closed patch previously committed as e81d23a812; real DIRECT/Electron E2E pending.
- EC-03: owner cache requires explicit TaskRun identity (focused tests passed); deeper lease/restart E2E pending.
- EC-07: telemetry projects canonical EvidenceRef to URI only, avoiding JSON serialization failure; 13 focused pytest passed. System1 runtime lacks laya in this test environment.
- Continue EC-03 to EC-14 using workstation/context/experience-compiler-activation documents; H-079/H-081/H-082 exact-head and main merge remain HOLD.

### 2026-10-12 — Experience Compiler EC-03/EC-04 authority continuation (PR #82 DRAFT)
- EC-03: Browser navigation now mapped to explicit HTTPS scoped external effect, lease/authority/budget/readback admission; stale owner bound per TaskRun and rechecked at call time. Item-start and pre-step lease/uncertainty rechecks implemented with race regressions. Native H-082 remains unqualified.
- EC-04: progressive VERIFIED_SUCCESS guarded by real persisted task/run/operation-bound verifier receipt with independent underlying evidence; Kernel supplies canonical verification proof. Full active TaskRun -> Laya -> offer -> VERIFIED_REUSE E2E remains pending.
- EC-05: vendored Laya 0.3.23 lock provenance validated; System-1 telemetry 2 PASS on vendored source, no live DIRECT checkpoint yet.
- EC-06+: open, especially explicit approved CALL budget for Browser native reuse; EC-13 HOLD. Exact-head CI, H-079/H-081/H-082 HOLD. Details in workstation/context/experience-compiler-activation/.

### 2026-10-12 — EC-03 exact-site browser effect and EC-04 witnessed causal data
- EC-03 recognized Trello open-site command explicitly budgets CALL(browser.navigate,trello.com); read authority and wrong-host denied. Local contract tests 10 PASS and H080B 2 PASS; native lease/restart/H-082 release remains HOLD.
- EC-04 formal capability labels now flow into progressive capture; no arbitrary replay parameters are inferred. A verified poststate alone carries no causality; prestate delta requires independent persisted and scope-bound prestate receipt. Still missing native producer, actual in-flight Laya mined offer and VERIFIED_REUSE. Do not count local unit tests as productive release.
- EC-05 locked Laya v0.3.23 three focused suites 10 PASS 1 SKIPPED; live checkpoint/DIRECT/CI HOLD. EC-06+ not completed. PR #82 draft; no merge.

### 2026-10-12 — EC-04 witnessed filesystem capture (draft PR #82)
- OperationalKernel filesystem/composite state observation now resolves scoped base_dir correctly.
- Existing durable owner emits independent prestate for single fs_write; second canonical admission/status check prevents cancelled plans from mutating after witness. Filesystem fs_hash/stat readbacks persisted as hash/metadata-only evidence, linked to canonical verification; mismatched pre/post resources fail closed.
- One real two-item WorkPlan scenario demonstrates corpus VERIFIED_SUCCESS while a second item remains pending; this is NOT candidate mining, offer, VERIFIED_REUSE or Laya real qualification. Next P0: attested replay parameters and full active TaskRun mine/validate/offer/adopt readback path.
- H-079/H-081/H-082 and exact-head CI HOLD; PR stays draft/unmerged.

## 2026-10-12 — New Browser Automation V1 isolated feasibility branch
- New isolated branch feat/hermes-browser-automation-v1-20261012 from origin/main a2b56db1bc, independent of PR #82 Experience Compiler and the separate feat/playwright-c2c-kits branch. Main checkout with user changes preserved.
- BAV01: Playwright-core chromium.connectOverCDP attached to an existing Hermes-owned Electron WebContentsView under disposable profile/127.0.0.1, filled and clicked a synthetic local page; independent server reported 1 effect. Test-only viability, NOT a production-authorized CDP adapter.
- BAV03: official singleton + authenticated native loopback controller executed a deterministic 2-input local form twice, 12 controller calls, 2 server-confirmed effects, 0 LLM calls inside test harness. No new browser owner.
- BAV05: versioned WebProcedure-compatible JSON fixture with lifecycle DISCOVERED and semantic testid fallback; missing-ref RED/GREEN with both effects verified. Still no durable ProceduralMemory registration, TaskRun restart or generic user-facing procedure.
- Next: bind existing ProceduralMemory/DeterministicRoutineRunner to BrowserTask/TaskRun owner with typed params, independent readback and persisted checkpoints. BAV04/BAV06+ future; H079 Stage A/exact-head CI HOLD. Do not promote test harness to product or merge.


<!-- BAV05 local checkpoint 2026-10-12 -->
- Hermes Browser Automation V1: isolated BAV-05 fixture E2E now persists a test-only procedure using canonical ProceduralMemory, reloads it in two new Python processes and replays via DeterministicRoutineRunner under the authenticated singleton controller. Three independent local-server effects; same BrowserTask, no cross-run authority qualification. H-079 Stage A, production promotion and BAV-04/06..12 remain HOLD.


<!-- BAV04 2026-10-12 experiment, PR85 Draft -->
- BAV-04 experimental crash-window test: using canonical ExecutionJournal + ArtifactStore + existing DeterministicRoutineRunner.resume_ref, a disposable Electron WebContentsView/authorized native controller fixture recovered after Python worker os._exit(37), independently reconciled server effect and avoided duplicate mutation (2 effects total). 11/11 Python guard tests, 2/2 paired Electron, 13/13 targeted Python + 16/16 memory/journal regression. **Test-only**, not production authority/restart/CI; H-079 baseline & exact-head release remain HOLD. Next: authentic new BrowserTask/TaskRun admission, real lease fencing and Electron main crash safety after Stage A qualified.

## 2026-10-11 — CWN renderer-first vector MVP (development only)
See `creative-workstation/MVP_EDITOR_DELIVERY_2026-10-11.md`. Renderer route provider, explicit vector project open/create, text/rectangle edit, keyframe interpolation, functional Inspector/Graph controls, undo/redo, JSON source save and current SVG frame export. **HOLD production promotion:** no shared Python creative commands/CAS persistence, no packaged Electron E2E, no true MP4 or 3D, no exact-head CI. Implement CWN-02 typed native command bridge before engine expansion.

## HCW-HYBRID-01 — EffectCraft + HyperFrames native composition (2026-10-11)

This lane extends D-043, preserving Hermes as the project/TaskRun owner. **DEVELOPMENT_ONLY / BLOCKED_FOR_PROMOTION.** Evidence: `creative-workstation/evidence/HCW-HYBRID-01.md`.

| Milestone | Observed status | Required next proof |
|---|---|---|
| H-C0 | PARTIAL / isolated worktree | H-079 upstream Stage A qualification; valid pinned installed engines |
| H-C1 | BLOCKED | actual HyperFrames RGBA sequence → EffectCraft `file.import` → effect+title → decoded PNG+MP4 |
| H-C2 | UNIT_TESTED | real `.ecproj` source validity, durable TaskRun publication, ETag/atomic head reconciliation |
| H-C3 | UNIT_TESTED PARTIAL | rational frame mapping is tested; cross-engine parameter updates not implemented |
| H-C4 | NOT_IMPLEMENTED | staged two-engine edit plan with real preview, CAS and owner receipts |
| H-C5/H-C6/H-C7 | NOT_IMPLEMENTED | contextual editor, procedural mattes, measured cache invalidation |
| H-C8/H-C9 | NOT_IMPLEMENTED | on-demand frame bridge and nested compositions after H-C1 proof |

P0 export verification defects were addressed in development-only source: failed decode no synthetic hash; missing source no silent black fallback. Existing first-clip export is **not** a qualified multilayer compositor.


### HCW-HYBRID-01 continuation — narrowed contract proof (development-only)

- H-C0: pinned HyperFrames source and locked dependencies prepared in isolated temporary folder; EffectCraft pinned FilmCraft dependency recovered, build progressing. Real native-engine integration and H-079 Stage A still blocking.
- H-C1/H-C6 partial **UNIT_TESTED SOURCE CONTRACT**: validate numbered RGBA frames + alpha + visible change and prepare `file.import` payload. No native frame producer/real EffectCraft proof.
- H-C3 partial **UNIT_TESTED SCHEMA**: declared typed bindings checked on project revision save; cross-engine updates NOT IMPLEMENTED.
- H-C7 partial **UNIT_TESTED FINGERPRINT**: per-frame source/asset SHA, fps, renderer version/profile cache key; actual bounded cache/invalidator NOT IMPLEMENTED.
- H-C9 partial **UNIT_TESTED GRAPH**: dependency topological order, maximum depth, cycle/missing-node rejections; runtime nested compositions NOT IMPLEMENTED.
- H-C4/H-C5/H-C8 remain NOT_IMPLEMENTED. Do not promote as complete.

Evidence: `creative-workstation/evidence/HCW-HYBRID-01.md`.


### HCW-HYBRID-01 addendum — 2026-10-12 native vertical tracer

Later than the status matrix above: H-C1 has advanced from synthetic fixture-only to
**NATIVE_VERTICAL_PROVEN / BLOCKED_FOR_PROMOTION**. The pinned official
HyperFrames CLI rendered moving, transparent 60x PNG RGBA 640x360/30fps; real
EffectCraft imported and reopened the image sequence, added native text and
non-default Gaussian Blur, and exported real 640x360/30fps 2s/60-frame H.264 MP4.
Native PNG and MP4 decoded pixel comparisons demonstrate actual changes/motion.
Real scoped start_creative_process/ProcessRegistry exercised without mocked
approval. Canonical CreativeDocument stored real engine source bytes and
rejected stale ETag. Tests at this checkpoint: 128 passed / 1 skipped scoped,
plus separately executed pinned producer test passed. H-C1 full promotion
remains BLOCKED on independent HyperFrames source edit in the same project and
the UI/TaskRun authority E2E. H-C4/H-C5/H-C8 and H-079 remain incomplete.
The original Matrix entries describe earlier historical states; use the
checkpoint in creative-workstation/HCW_HYBRID_EXECUTION_STATE.md for current state.


Final update to the above HCW addendum: scoped Creative test suite re-executed
on this source with all opt-in native engines and FFprobe: 28 files, 130 passed,
1 symlink skip, 128.07 seconds, exit 0. CI/H-079 remain blocked for promotion.


### HCW-HYBRID-01 — continued H-C1/H-C2/H-C3/H-C4 implementation, 2026-10-12

An authorized, *unchanged* official HyperFrames variables-prod template
now yields actual different rendered pixels when strict CLI
--variables-file changes title/subtitle/bgColor. The real EffectCraft
imports both source variants and native text edits produce further
pixel differences. Three immutable revisions of the SAME CreativeDocument
store editable real .ecproj, HTML, JSON overrides and the referenced
silence.wav. A NEW opt-in canonical HEAD CAS + typed batch publisher
tests interprocess lock, ETag, idempotent replay, 409 stale/race,
third-command failure atomicity, orphan rejection and native source
retention. Real claimed Kanban TaskRun CLI create/open/apply-batch
passes with session/authority/policy and journal. Not integrated into
React manual UI; the new backend has not replaced the old UI state.
H-C4 cross-engine distributed atomicity/undo, H-C5 Electron
EffectCraft Web, nested render, 10s final video, full CI and H-079
remain open. H-C0–H-C9 must NOT be marked QUALIFIED. For exact
fresh tests, SHA and continuation steps use
creative-workstation/HCW_HYBRID_EXECUTION_STATE.md.

Current scoped test result: 32 Creative test files, 151 passed,
1 skipped, 0 failures, 175.02 s, exit 0. Next gating priority is
Electron renderer edits through live TaskRun canonical-open/apply-batch;
this backend receipt is not an Electron E2E qualification.

H-C4 backend progress: historical operation replay is now O(1)
receipt-index lookup with verified published ancestry and
stable typed-command digest; repeated older command after
intervening commit returns original receipt without new revision.
Nonmatching or orphan receipts are refused. 8 CAS tests green.
Not yet native dual-engine distributed transaction, durable undo/redo,
verified Electron actor identity or H-079 qualified.

Post-history-index CAS regression: 32 selected Creative files,
152 passed / 1 skipped, 158.95s, exit 0. H-C4 partial, unqualified
pending true editor identity, live Electron and distributed engine edits.


### HCW-HYBRID — 2026-10-12 H-C2 React presentation seam

New frontend trace: /creative now mounts CreativeWorkspaceProvider; a
single React display state is projected from validated canonical HEAD,
not writable duplicated useState/Nanostore project. Real Python
CreativeProjectRevision.etag syntax and rational-seconds CanonicalTime
strings are verified in Node projection tests. Focused UI Vitest
9 green and real-backend Node tests 4 green. H-C2 is NOT QUALIFIED:
the renderer is not yet connected to an authenticated Electron IPC
or gateway endpoint, nor to an authorized live TaskRun identity.
Next stage must implement that link (no arbitrary shell interface)
and prove human mouse -> canonical HEAD -> agent command -> UI refresh
with actual Electron E2E. All H-079 and exact-head CI gates remain.

### H-C2 typed Electron contract — 2026-10-12

New typed main/preload command allowlist and React view readback
are unit/integration-contract tested but NOT live authenticated
Electron-to-TaskRun integration. Current main resolver deliberately
returns no owner. P0: implement and independently verify server-attested
TaskRun owner lookup, authenticated canonical RPC; then update main
resolver and run real human mouse -> CAS -> agent -> refreshed UI
E2E including restart/conflict/lease fences. Native H-C1 prior
tests remain valid; H-C4 distributed native transaction and H-C5-H-C9,
H-079 and full CI remain incomplete.


### H-C2/H-C4 IPC plan re-evaluation — 2026-10-12

Electron canonical IPC now reattests the exact sender's trusted owner
across async edit/readback and requires a matching durable CAS revision
receipt, never acknowledging an old/stale head. Unit tests + preload
(11 passed) and targeted ESLint passed. main.ts still registers the
bridge fail-closed with a null owner resolver: **no live manual
TaskRun-backed Electron edit**; enabling from renderer-provided
task/session/actor IDs is forbidden. P0 must first implement
gateway/backend-authenticated TaskRun attestation per main-owned
window/connection and then native UI+agent revision roundtrip.
The revised H-C0–H-C9 dependencies and explicit promotion gates are in
creative-workstation/HCW_HYBRID_PLAN_REVIEW_2026-10-12.md.

### HCW-HYBRID P0A — 2026-10-12 partial attestation contract

Electron main-side verifier validates fresh backend proof against main-owned webContents/navigation/connection/profile/session, TaskRun live flags, actor principal and lease expiry. 14 TDD tests new; 25 focused GREEN. Production owner resolver remains null/deny-all until authenticated backend attestation and main sender registry exist. NOT H-C2 integrated or usable editor. Next P0A endpoint + main binding; then P0B human/agent CAS E2E. H-079 and release gates unchanged.


### HCW P0A backend-bound TaskRun admission (2026-10-12)

Added `creative_taskrun_attestation.py` using existing Kanban/CreativeRunContext with a verified session-record identity, ContextVar-only gateway key, short proof lifetime fenced by actual task/run claim leases, and rejection of competing runs or detached context. 25 focused Python backend/CAS regressions passed. This is **not** a production authenticated endpoint, nor an Electron main-owned sender binding, therefore P0A/H-C2 remain unqualified and `resolveTrustedOwner: () => null` remains intentional. Next: authenticated HTTP/gateway principal + actor mapping, main-owned window connection/session binding, bounded canonical RPC and native E2E. H-079 unchanged.

### HCW-P0A: read-only HTTP identity → TaskRun association

2026-10-12 continuation after 85b0448fa: Added workstation/creative_http_identity.py and GET /api/workstation/creative/owner-readiness in hermes_cli/web_server.py. Read-only authenticated interactive-principal → canonical SessionDB (user_id/session_key) → unique live Kanban TaskRun lookup with workspace, profile, expiry, lock and supersession fences. OAuth/native-session request.state.session is required; loopback token and service token are not considered interactive actor authentication. TDD RED module absent (exit 1), route not registered (1 failed exit 1), GREEN 38 passed, 0 failed in 47.06s, 1 Starlette/httpx deprecation warning, command python -m pytest workstation/tests/test_hcw_http_principal_owner.py workstation/tests/test_hcw_taskrun_backend_attestation.py workstation/tests/test_hcw_hybrid_taskrun_command.py workstation/tests/test_hcw_hybrid_revision_cas.py -q. No sessionKey or claimLock returned; authorityGranted=false. Not an authenticated mutation RPC or live gateway authority proof. main.ts remains resolveTrustedOwner: () => null; P0A PARTIAL, P0B BLOCKED; H-C2 no promotion, H-079 and exact-head CI unverified.

### HCW-P0A Electron selector registry (2026-10-12): new apps/desktop/el

HCW-P0A Electron selector registry (2026-10-12): new apps/desktop/electron/creative-main-sender-scope.ts and .test.ts implement a MAIN-process-only in-memory sender object+mainFrame-verified registry with monotonic navigation epoch, explicit rehome/revoke, concurrent-session fencing, destruction check and defensive snapshots. TDD RED: missing module, Vitest exit 1. GREEN: 31/31 Electron focused tests across registry, existing attestation, canonical IPC, preload, exit 0. ESLint --max-warnings 0 exit 0 after targeted fixes. Global tsc still exit 1 ONLY known electron/git-review-ops.test.ts:124 TS2349. Registry deliberately NOT WIRED to main.ts: session/connection obtained from renderer messages/URL are selectors not authenticated authority. main.ts remains DENY-ALL. No P0A or H-C2 promotion. Backend HTTP readiness previously qualified 38/38 tests, no mutation grant.

# Hermes Work — Plano operacional 80/20 e prompts executáveis (25/10/2026)

**Situação:** PREPARADO / NÃO IMPLEMENTADO. Checkout inspecionado: `C:\Github\hermes-agent`, `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`. Este HEAD é apenas referência: revalidar ao implementar. Não efetuar reset, stash, switch, merge ou push em checkout compartilhado. Os prompts não são autorização de release, efeitos externos ou edição de arquivos reclamados por outros agentes.

## Evidência atual — muda a ordem antiga

- **TypeScript GREEN:** `npm run typecheck --workspace apps/desktop` terminou com exit **0** em 25/10. Os seis erros descritos no relatório de 23/10 **já foram corrigidos**; não abrir missão artificial para repará-los.
- `tools/browser_workstation.py::_dispatch` (aprox. L896–1110) já preserva TaskRun, `STALE_RUN`, `operation_id`, telemetria, redaction e projeção. `workstation_routed_browser_handler` (aprox. L1252) já preserva lease humano e isolamento entre navegador interno e fallback. `_validate_navigation` já existe.
- `workstation/browser_guards.py::GuardRegistry` é **async** e seu `binding_guard` é mais amplo que o contrato canônico. Uma ligação indiscriminada ao dispatcher síncrono seria regressão; o `create_default_registry` parece sem consumidor de produto. `workstation/token_estimate.py::estimate_json_output_tokens` está presente, mas não há uso comprovado no tráfego final ao modelo.
- `project_model_browser_payload` já possui projeção lossless de inventário e cache. Telemetria de navegador `workstation/telemetry/browser_observation.py` **não pode registrar DOM, URLs, corpos, credenciais ou conteúdo privado**.
- `apps/desktop/electron/workstation-browser-runtime.ts::startLearning` já resolve `ownerTaskId → sessionHost → storedSessionId`. Ainda falta prova real de pergunta no chat correto, captura não sintética e compilação.
- **WhatsApp e Site Ops são frentes concorrentes, com claims ativos.** M1/M2 não devem ser refeitos. M3 está em HOLD para metadados nativos de destinatário/direção/ACK apesar dos RED/GREEN sintéticos; M4–M6 não estão aprovados. Consultar `workstation/context/WHATSAPP_RELIABILITY_2026-10-24.md`, `WHATSAPP_IMPLEMENTER_PROMPTS_2026-10-24.md` e `engineering-journal/whatsapp-catalog-stagea-hold-20261025.md`.
- **Claims ativos em 25/10:** `chatgpt-whatsapp-m3` reivindica `tools/browser_workstation.py`, executor WhatsApp, testes e documentos centrais; `chatgpt-siteops-contract` reivindica `apps/desktop/electron/ipc/site-ops.ts`, testes e script JS legado; `site-ops-migration` cobre migração antiga. Não editar sem liberação explícita/transferência.
- **Gate Stage A:** consultar regras upstream-first. Exceção de H-079 para outra missão **não é transmissível**. Sem qualificação ou autorização expressa desta missão: somente testes/patches isolados; runtime HOLD.

## Sequência e agrupamento

| Ordem | Prompt | Prioridade | Justificativa | Dependência |
|---|---|---|---|---|
| 1 | Q1 — Browser Guards e erros | P1 | alto risco de duplicar autoridade; investigação focada e implementação mínima | owner de browser liberado; Stage A |
| 2 | Q2 — Tokens/observabilidade | P1 | medir economia real exige baseline próprio; não misturar com segurança | Q1 estável |
| 3 | Q3 — Aprender E2E | P1 | atravessa renderer/chat/compilador; merece contexto próprio | TypeScript GREEN; claim |
| 4 | Q4 — Site Ops único executor | P1 HOLD | contrato mutante e IPC sob ownership paralelo | owners Site Ops e WA; Stage A |
| 5 | Q5 — WhatsApp M3 → gates M4–M6 | P1 HOLD | efeitos externos e privacidade, sem duplicar M3 | M3 owner conclui e prova browser |
| 6 | Q6 — Gmail/Email batch | P2 | provider e OAuth constituem outro domínio de falha | interfaces maduras; autorizações |
| 7 | Q7 — Bootstrap/attach medidos | P2 | só otimizar com distribuição real cold/warm | backend estabilizado |

Q1 e Q2 podem compartilhar uma **mesma sessão Claude** em ordem, mas devem ter commits/test gates distintos se alterarem o mesmo arquivo. Q4 e Q5 **não rodar em paralelo** sobre o executor/Browser. Não dedicar um prompt para “reinvestigar todo repositório”; cada prompt inclui preflight mínimo.

## PROMPT Q1 — Guards sem duplicar a autoridade do Browser

**Objetivo:** corrigir rejeições tardias reais, se houver, sem substituir o roteamento canônico. Repositório `C:\Github\hermes-agent`, branch `main`. Antes de editar: verificar HEAD/status, claims, `AGENTS.md`, `workstation/AGENTS.md`, `tools/AGENTS.md`, Stage A / exceção desta missão. Se `tools/browser_workstation.py` estiver reclamado por M3, não editar; fornecer patch isolado/handoff.

**Pontos exatos:** `tools/browser_workstation.py::{_validate_navigation,_dispatch,workstation_routed_browser_handler}`; `workstation/browser_guards.py::{navigate_scheme_guard,binding_guard,browser_connected_guard,create_default_registry}`; `workstation/browser_error_messages.py::classify_browser_error`; testes `workstation/tests/test_browser_workstation_route.py`, `test_browser_session_run_isolation_p0.py`, `test_browser_operational_admission.py`.

**Execução:** (1) reproduzir RED para rejeição indevida ou round-trip evitável. (2) Comparar regras atuais com guards propostos: o guard experimental permite esquemas que `_validate_navigation` pode vedar; não afrouxar allowlist. O `binding_guard` exige IDs também para operações read-only legítimas; não colar na rota síncrona. (3) Só havendo RED comprovado, criar predicado puro síncrono mínimo junto à validação existente, antes de `_request_json`, emitindo erro estruturado canônico. Evitar `asyncio.run`, outro controlador, novo sistema de autorização, fallback após efeito incerto. (4) Revisar diffs duas vezes e registrar causa raiz.

**Aceite:** testes canônicos via `scripts/run_tests.sh`: navegação proibida nunca chama controlador; read-only legítimo preservado; bind parcial = `STALE_RUN`; lease humano bloqueia; timeout pós-mutação = `UNCERTAIN` sem retry; retorno continua redigido. Se não aparecer RED real, **NO_CHANGE com evidência** é sucesso melhor que inserir código morto. Documentar razão, caminhos, RED/GREEN, STATUS e limites.

## PROMPT Q2 — Economia de tokens mensurada, sem perda de refs

**Objetivo:** integrar estimativa de consumo na saída Browser se acrescentar valor verificável, sem reescrever métricas existentes. Verificar HEAD/status/claims/Stage A e owner de `tools/browser_workstation.py` antes de editar. **Pontos:** `workstation/token_estimate.py::{estimate_json_output_tokens,estimate_tool_output_tokens}`, `tools/browser_workstation.py::_dispatch` (bloco final L1076–1110), `project_model_browser_payload`, `workstation/telemetry/browser_observation.py::emit_native_browser_observation`, `workstation/telemetry/browser_optimization_metrics.py`, `workstation/tests/test_browser_model_payload_projection.py`.

**Execução:** (1) fixtures sintéticas de snapshot: refs, views, Unicode, dados privados fictícios, browser cache on/off. (2) Para payload raw e projected, medir bytes e tokens estimados com funções existentes; não comparar duas sessões com conteúdo diferente. (3) Conferir se métricas atuais já estimam economia por chars para não duplicar o mesmo ganho. (4) Se justificar, usar somente contadores numéricos bounded após a projeção e antes do JSON de saída; nunca gravar DOM, URL, corpo, screenshots, tokens de acesso. (5) Não aplicar `slice_text_by_estimated_tokens` diretamente a snapshots endereçáveis nem truncar recibos/erros. Confirmar `model_facing=False` sem mudança.

**Aceite:** endereçabilidade, refs e elementos preservados; fallback lossless em payloads não reconhecidos; comparação raw/projected reproduzível, métrica rotulada **estimativa**, nunca “tokens faturados”; ausência de vazamento no evento; benchmark repetível p50 com mesma fixture. Executar `scripts/run_tests.sh workstation/tests/test_browser_model_payload_projection.py` e regressões pertinentes. Se não houver ganho adicional frente à instrumentação já presente, preferir **NO_CHANGE** e registrar justificativa.

## PROMPT Q3 — Aprender realmente funciona no chat e na captura

**Objetivo:** provar `Aprender → gesto/evento → pergunta no chat correto → resposta → evidência/candidato` sem falsos positivos. Verificar HEAD/status/claims/Stage A; baseline TS atual passou. **Alvos:** `apps/desktop/electron/workstation-browser-runtime.ts::startLearning` (L2453–2510), `workstation-learning-session.ts::{startFrameCaptureLoop,captureNextFrame}` (L968–1050), ponte/hooks de chat identificados por import; testes `workstation-learning-session.test.ts`, `workstation-learning-capture.test.ts`, `workstation-learning-vertical-slice.test.ts`, `workstation-browser-ipc-learning-owner.test.ts` e hook UI real.

**Execução:** RED de duas sessões A/B e duas abas: pergunta A nunca vai para B após troca/reconnect; dedupe por eventId; ausência de ID real falha fechado. Checar `ownerTaskId → task.sessionHost → storedSessionId` sem fallback artificial. Testar captura `captureFrame` retornando Buffer real sintético local, stop/discard/restart, frame index e falha de escrita observável; não contar canvas colorido simulado como prova de captura real. Preservar redaction, não sobrepor cards no Browser/canvas e não criar outro store. Depois abrir Hermes real em perfil de teste, ativar Aprender numa ação inofensiva e conferir journal/renderer/compilador. Sem WhatsApp/send externo.

**Aceite:** Vitest focado com isolamento e dedupe, `npm run typecheck --workspace apps/desktop` GREEN, E2E visual com prova de captura e pergunta correspondente; se UI inacessível, **UNIT_GREEN_NATIVE_HOLD**. Documentar IDs correlacionados de teste, não dados privados. Não alegar compilação se nenhum candidato/evento foi produzido.

## PROMPT Q4 — Site Ops e IPC: um único executor mutante

**Objetivo:** reconciliar o legado Site Ops com o Browser nativo, sem roteador CDP paralelo. **Antes de tocar arquivos:** claims de `chatgpt-siteops-contract`, `chatgpt-siteops-sim`, `site-ops-migration`, `chatgpt-whatsapp-m3`; Stage A/exception desta missão e HEAD. Se ocupado, não disputar ownership: relatar HOLD e patch disjunto.

**Alvos:** `apps/desktop/electron/ipc/site-ops.ts`, `site-ops/scripts/site-ops/whatsapp-web.mjs`, `site-ops/skills/whatsapp-web-ops/SKILL.md`, `apps/desktop/electron/ipc/site-ops.test.ts`, `site-ops-mutating-gate.test.ts`, `site-ops-auto-heal.test.ts`, `workstation/tests/test_siteops_mutation_boundary.py` e `test_site_ops_e2e.py`.

**Execução:** enumerar comandos read-only vs mutantes; `send-message` no JS legado deve recusar mutação direta ou encaminhar somente por ferramenta canônica com TaskRun/OperationId/lease/approval; não ampliar IPC para `spawn` irrestrito. Montar simulação **sem rede, sem WhatsApp autenticado e sem envio** com IPC → autorização → executor único (mock) → recibo; testar replay do mesmo operation_id, falha pré-efeito, falha pós-efeito = `UNCERTAIN`, erro de ownership, falha de auto-heal, persistência de mapa somente sob verificação. Proteger redaction.

**Aceite:** Vitest dos três módulos, testes Python pelo runner canônico, typecheck GREEN, nenhum side-effect por CDP legado; 5 skipped E2E não qualificam o runtime. Se `agent-browser` ou Browser nativo indisponível, classificar **NATIVE_HOLD** sem retirar skips artificialmente. Entregar matriz de operações, owner, evidências, e handoff.

## PROMPT Q5 — WhatsApp: finalizar M3 existente; M4–M6 só com gates

**Objetivo:** trabalhar a partir de M3, sem recomeçar M1/M2 ou criar banco/dispatch novos. Pré-checar HEAD, claims, Stage A, `workstation/context/WHATSAPP_RELIABILITY_2026-10-24.md`, `WHATSAPP_IMPLEMENTER_PROMPTS_2026-10-24.md` e `engineering-journal/whatsapp-catalog-stagea-hold-20261025.md`. Alvos: executor `workstation/integrations/hermes/whatsapp_browser_executor.py`, `tools/browser_workstation.py::whatsapp_send_message`, testes `workstation/tests/test_whatsapp_browser_executor.py`, `tests/tools/test_whatsapp_browser_tools.py`.

**Execução:** primeiro READ-ONLY verificar como Browser nativo fornece recipient, direção OUTBOUND, body/digest e ACK reais; não inferir sucesso por `msg-meta` genérico, bolha antiga ou composer vazio. Se metadados ausentes, **HOLD** e propor seam readback segura, sem desbloquear envio. Se completos, provar novos IDs associados a destinatário/corpo/ACK; operação reservada antes de efeito; mensagem anterior homônima não é prova; timeout pós-clique = `UNCERTAIN` e bloqueia retry automático após restart. Não usar aprovação por campo de texto `approved_by`; nunca expor PII/model result. Só liberar M4 (batch/approval), M5 (read incremental) e M6 (anexos/E2E/métricas) quando gates M3 nativos e autorização de etapa estiverem presentes. **Nenhum envio real sem consentimento explícito posterior.**

**Aceite:** negative controls novos e antigos, runner canônico Python, testes TypeScript de admission, recibo causal completo e redaction. Resultado GO/HOLD fundamentado; se HOLD, parar no M3, não produzir alegação de release.

## PROMPT Q6 — Gmail/Email Batch: contratos sintéticos antes de OAuth real

**Objetivo:** finalizar a prova do envio em lote por email, sem usar envio real para fazer testes. Revalidar HEAD/claims/Stage A. **Alvos:** `workstation/integrations/hermes/email_provider.py::{GmailApiProvider,GmailBrowserFallbackProvider,EmailBatchSender}`, `workstation/tests/test_email_provider.py`, `workstation/prefabs/integration.py`; localizar o wiring da função que efetivamente chama `send_batch`, sem presumir que o símbolo histórico `wa_worker` ainda existe.

**Execução:** mapear call chain ao provider; exercitar FakeProvider e 3 destinatários sintéticos para sucesso, auth_missing, partial timeout e retry. Preservar identidade de cada item, idempotency key, corpo/segredo fora da telemetria, no-fallback silencioso quando OAuth falha; browser fallback não pode enviar sem autorização/canal correto. Se faltar seam, patch mínimo na classe existente — não novo dispatcher, store ou infraestrutura paralela. Autenticação real em UI humana é etapa posterior; preparar ensaio de 3 mensagens mas **não executar** sem aprovação explícita e endereço/conteúdo revisados.

**Aceite:** testes provider+batch via runner canônico, sem envio real nem credencial no log, `UNCERTAIN` não duplica, medição de latência por item. Meta ≤1 msg/min **não validada** sem E2E na rede. Registrar GO/HOLD, falhas e artefatos.

## PROMPT Q7 — Backend/startup: confiabilidade e desempenho medidos

**Objetivo:** impedir duplicação de backend e reduzir o gargalo realmente dominante, não micro-otimizar baseado em dados de 23/10. Revalidar HEAD/claims/Stage A. **Alvos:** `workstation/start.ps1`, `workstation/install.ps1`, `apps/desktop/electron/host-backend-attach.ts`, `apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts`, `desktop.log` [boot-perf], script existente `workstation/scripts/extract-boot-perf.ps1` quando disponível.

**Execução:** controlar versão Node/Python/cache, perfil e processos isolados; colher 5 cold e 5 warm com start/end, backend-ready/renderer-hydrated, p50/p95 (sem matar apps do usuário). Instrumentar reattach de backend existente, reap idle e corrida entre duas instâncias; `/api/health` uma vez positivo não prova recuperação depois do reap. Apontar maior fatia do wall time, formular RED e corrigir **um** seam; testes de spawn gate, no second backend, ledger stale, failure recovery. Não desligar WARP/Tailscale, desativar AI Control ou restaurar CDP externa por padrão como atalho.

**Aceite:** Windows smoke + testes de attach + typecheck, P50/P95 before/after comparáveis, prova de single backend e logs privados. Sem ganho claro ou causa verificada, **NO_CHANGE** documentado é aceitável.

## Contrato comum: acrescentar ao prompt executado

Você é analista crítica **e** engenheira implementadora. Não copie sugestão automaticamente: confrontar símbolo/linha com HEAD e, se necessário, `git log -p -S`; pode melhorar a solução se justificar e testar. Quando há autorização/owner, **implemente**, não encerre com proposta. Use RED→GREEN, 1–2 testes invariantes, revisão de diff e verificações de runtime. Não criar novamente executor, DB, Browser controller, memória ou stores existentes.

Antes de escrever: `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, `python workstation/scripts/multi_agent_coordination.py status`, AGENTS das áreas, `workstation/context/README.md`, Stage A ou exceção **expressa desta missão** e reivindicação exclusiva dos caminhos. Proibidos reset/clean/stash automático, branch antiga, modificação de claim de terceiro, bypass de lease, operação mutante sem prova ou envio externo não aprovado.

Ao finalizar: arquivos/símbolos, diff, RED e GREEN com contagens, status de integração, E2E nativo vs sintético, riscos pendentes, GO/HOLD e documentação no journal **quando houver owner**. Se faltar gate, entregar um RESUME PROMPT autossuficiente com HEAD, WIP, dono, único próximo RED, testes e restrições. Não usar um resultado mock para dizer “produto aprovado”.

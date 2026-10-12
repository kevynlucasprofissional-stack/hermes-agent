# Handoff executável de implementação — após auditoria
Esta missão de auditoria NÃO modifica produção e NÃO autoriza merge. O executor posterior deverá primeiro reconciliar novos commits e arquivos modificados; o checkout local de referência é 9fffa7f em fix/hermes-oneclick-lock-startup-20261011 e main é a2b56db. Nunca resetar/dropar alterações existentes da árvore.

## Gate 00 — preflight e owners
- git status --short; git rev-parse HEAD; comparar main vs branch; ler workstation/AGENTS.md, workstation/ROADMAP.md e status H-079/H-081/H-082 no HEAD corrente.
- Proibir .gitignore bypass ou envio de dogfood/sessions/HTML privados, secrets, cookies e local artifacts.
- Mapear composition root / entradas de Agent/Workstation; não alterar modelo de autoridade.
- Executar testes em ambiente onde pytest e dependências estejam instalados. No Python 3.14 deste exame pytest NÃO está instalado; não instalar automaticamente sem planejamento.

## Gate 01 — instrumentação primeiro
Arquivos: workstation/experience_compiler/compilability_monitor.py, workstation/integrations/hermes/tool_observer.py, workstation/telemetry.py.
- Eventos estruturados: capture_observed, closure_accepted, prefilter_skip_reason, decision_stage, mine_attempt, mined_candidate, validation_attempt, denial, offer_created, adoption_attempted, adopted_verified, router_hit/miss, drift.
- Tipo/proveniência: task_id, run_id, operation_id, capability id/version, receipt refs redigidas, reason codes. Métricas desconhecidas ficam null, nunca zero fictício.
- Expor summary read-only sem payload privado e sem mutating endpoints.
- Testes: enumeração exata, monotonic outcomes, contagem duplicata/dedupe e disabled telemetry fail-open para produto (não para permission).

## Gate 02 — cold start e mineração verificada
Arquivos: workstation/experience_compiler/{progressive,corpus,compiler,lifecycle}.py, workstation/kanban.py, workstation/operational_kernel.py.
- Verificar que a conclusão canônica emite VERIFIED_SUCCESS *somente* para amostra vinculada a leitura posterior/owner evidence; garantir que nova observação chegue ao monitor sem duplicar store/truth.
- Testes: observed/uncertain continuam não positivos; accepted owner-linked pode virar VERIFIED_SUCCESS; negative counterexamples; scoped mine não lê candidatas de outro TaskRun.
- Sem alteração na ExperiencePromotionPolicy para facilitar artificialmente resultados.

## Gate 03 — qualificação e canário que discrimina
Arquivos: lifecycle.py:create_local_canary_validation_provider, compilability_validation.py, control_plane/verification.py e run_local_adoption.py.
- Primeiro família filesystem em diretório temp isolado. Sonda positiva e negativa devem executar/verificar condições semanticamente ligadas ao step/contract da candidata, não apenas escrever arquivo independente.
- Validar fingerprint, evidence refs, target, lease, proof of delegated scope, replay false/timeout/drift.
- Fechar fail-closed em qualquer ausência, exception, ref estranha e material desconhecido.
- Testes negativos obrigatórios: ghost refs, wrong task/run, mismatch verifier, changed step, authority revoked, uncertain mutation.

## Gate 04 — adoção real
Arquivos: workstation/integrations/hermes/operational_resolution.py, run_local_adoption.py, workstation/run_adoption.py.
- No começo de turno, não reaproveitar autoridade de sessão anterior. Só adotar pending equivalent items no mesmo TaskRun, com DIRECT HMAC attested, scoped policy real e readback por primitive.
- Sem retry cego após dispatch uncertain; after effect unknown manter WAIT/HANDOFF.
- Testar faixa 3 exemplos aceitos -> próximo item efetivamente adotado, 0 chamadas intermediárias desnecessárias de System-2 quando admitido. Registrar provider calls reais e status VERIFIED.

## Gate 05 — descoberta e visibilidade
Arquivos: tools/registry.py, tools/toolsets.py, model_tools.py (localizar caminhos efetivos), workstation/control_plane/router.py, apps/desktop.
- Primeiro read-only capabilities catalog e reasons, com perfis respeitados. Comprovar toolset instalado/habilitado e funcional, não apenas skill mention.
- UI Capability Explorer inerte: read API + frontend, capability ref/version, steps, edges, guards, verifier, provenance e telemetry evidence; no new dispatcher.
- Testes: sem licença/tenant/permission, conteúdo indisponível; dados UNKNOWN explicitados; 0 mutations pelo viewer.

## Gate 06 — editor experimental
- Definir adapter somente para subconjunto de steps/edges com round-trip lossless; serializar via API canônica.
- Toda edição é revision DISCOVERED com fingerprint novo; versão PROMOTED anterior imutável. Verificar rejeição de loops, branches e free-form expressions não suportadas.
- Testar compactação/conversão e diff, no inheritance of authority.
- Manter artefatos e owners existentes (Kernel/Registry/Policy) como execução única.

## Gate 07 — measurement & CI
- Rodar testes unitários e E2E nativo Electron em branch isolada; comparar execução E2E com baseline; qualificar exact-head CI.
- Métricas: verified completions, false reuse, ratio de candidatos, rollback/restart, LLM calls/tokens, cost/per verified outcome, p50/p95.
- Condições para negar merge: vermelho segurança, verificador sintético, step sem contrato, leak de dados, regressão de autoridade, sem readback.

## Final
Entregar PRs pequenos segregados por owner e pacote, relatórios com SHA HEAD, comandos e saídas, evidências E2E e casos negativos. NÃO fazer merge automático; o maintainer decide após qualificação.

## Correção P0 detectada depois do primeiro levantamento (EC-00)
Antes de ampliar taxa de mineração, corrigir workstation/integrations/hermes/run_local_adoption.py:162–172 versus workstation/run_adoption.py:456–463. O owner atual recebe readback_fn=None e _readback_fns em campo não consumido pelo método can_readback(). Oferecer um callback readback_fn(primitive,args,raw) que faça dispatch tipado ao readback autorizado, ou interface formal equivalente, mantendo owner.can_readback condicionado a callback disponível por primitiva. Nunca marcar todas as primitives como readback-capable incondicionalmente. Teste de owner DE PRODUÇÃO: build_run_adoption_owner -> can_readback('write_file') verdadeiro apenas com handler; aplicação de readback real; negativa expected hash mismatch; de qualquer mutação com readback ausente => denied sem dispatch; sem fallback permissivo. Revisar a semântica dos readbacks de browser_snapshot e trello_api_get, que atualmente validam URL/shape usando raw e podem não ser independentes. Main GitHub confirma esse bug estrutural no commit a2b56db1.

**Teste regressivo específico que falta:** test_online_compilability_safety.py:115–124 injeta DurableRunAdoptionOwner(readback_fn=self.readback), não exercita build_run_adoption_owner real; adicionar teste de integração que chame factory sem owner pré-injetado, verifique can_readback/readback, e troca de TaskRun no mesmo agent com cache invalidado e dispatch/authority bound ao novo task.
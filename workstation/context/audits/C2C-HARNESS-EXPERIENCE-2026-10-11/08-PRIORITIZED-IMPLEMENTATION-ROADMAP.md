# Roadmap priorizado: aprendê-lo, reutilizá-lo e torná-lo visível
Baseline: branch local 9fffa7f, main a2b56db. Hipóteses de benefício ainda não medidas empiricamente.

## Prioridade 0 — provar o funil em produção
P0.1 Instrumentar condição real de entrada no monitor: enabled, effective mode sem segredo, downgrade_reason, rate de capture, estágio do Laya, reasons e sample refs. Alteração mínima: compilability_monitor.py e telemetry.py. Aceite: counters por TaskRun derivados de eventos, unknown explícito, ausência de gravação de segredos.
P0.2 Demonstrar canal cold-start adaptive -> ACCEPTED VERIFIED -> corpus -> scoped mine com identidade task/run; corrigir lacunas observadas, não inventar verificador. Owners: tool_observer.py, corpus.py, kanban.py, lifecycle.py, progressive.py. Aceite: trace source-to-destination, replay independente e cross-run candidata sem promoção indevida.
P0.3 Realizar canary production-owned pequeno, isolado, com teste negativo discriminativo de contrato e real readback. Owners: lifecycle.py, compilability_validation.py, run_local_adoption.py. Aceite: trocar dado esperado/step/target faz reprovar; não usar teste que apenas vê arquivo gerado.
P0.4 Run-local adoption de operação equivalente em mesmo TaskRun somente com DIRECT attested e delegado; clamp scope por item; nenhum retry mutativo sobre incerteza. Owners: operational_resolution.py, run_adoption.py, effect_authority.py, control_plane. Aceite: 4º item com verified reuse; controle negativo de lease/profile/tenant/run e mudança de destino.
P0.5 Melhorar entrega de capability ao router e ferramenta/catálogo visível no Hermes Agent/Work; distinguir candidates de promoted. Owners: operational_capabilities.py, control_plane/router.py, tools/toolsets e tools/registry. Aceite: por toolset ativo discovery explícito e ocultação quando desativado.

## Prioridade 1 — oportunidade durável e observabilidade
P1.1 Persistência por evidence revision com backoff/cooldown e nova elegibilidade após fatos materiais; limites continuam por janela de CPU/memória, não bloqueios irreversíveis. Owner compilability_monitor.py e ArtifactStore/ExperienceCorpus existentes. Aceite: teste restart + retry revisado + no spinning identical deterministic failure.
P1.2 View READ-ONLY Capability Explorer e funil verified: estado, origem, steps, verifier, effect class, last reuse, denial reasons, uncertainty UNKNOWN. UI apps/desktop React. Aceite: todos dados com provenance, nenhuma ação mutativa.
P1.3 Retrieval de candidatas por semântica + score de utilidade somente após contract eligibility; controlar falsos matches, detectar drift. Inspirado Ratchet/Voyager, sem permitir fuzzy match criar autoridade.
P1.4 Melhorias de desempenho em Browser e descoberta de ferramenta conforme contadores do dogfood; evitar usar contagem bruta browser_console como redução de custo. Aceite: p50/p95 e calls por VERIFIED outcome em cenário pareado.

## Prioridade 2 — revisão humana de capacidades
P2.1 Visual projection lossless para subset sequencial; unknown nodes em modo somente leitura.
P2.2 Editor de parâmetros tipados / diff semântico com revisão imutável DISCOVERED, novo fingerprint e downgrade de evidência.
P2.3 Composição de capabilities existentes, parâmetros/dependencies explicitamente mapeados e validação isolada. Bloquear cycles, effects sem verifier, runtime indefinido.
P2.4 Histórico de versões, rollback de definição (NÃO desfazer automaticamente efeitos externos) e execução em modo inspecionável.

## Prioridade 3 — workflows gerais (condicional)
Ramos/loops/triggers/esperas e integrações externas, conforme demanda real e suporte do Kernel. Escolher adaptadores em vez de importar workflow engine n8n/Activepieces. Exige design de IR, policy, versioning e migrações e benchmark.

## Ganhos e riscos
Nenhuma estimativa percentual de economia é sustentada hoje. Para cada fase registrar baseline e pós-teste: verified outcomes, LLM calls medidos, provider tokens, p50/p95, false reuse, restart recovery e custo total. Ganho aparente com mais falha/mutação não verificada NÃO é aceito.

## Dependências
P0 provas -> P1 telemetria/observabilidade -> P2 edição -> P3 eventual engine de grafos. Algumas melhorias P1 Browser podem ocorrer antes, desde que não interfiram em ownership atual. Não mesclar fase sem gates exact-head e E2E.

## Rejeições temporárias
- Importar engine n8n como executor do Hermes: viola single owner e traz licença restritiva.
- Ativar DIRECT por simples flag/string sem atestado e verificador.
- Promover após uma única repetição sem causalidade e replay.
- Tratar canary genérico como prova de qualquer procedure.
- Editor capaz de alterar capacidade PROMOTED in-place.

## P0 URGENTE — corrigir readback owner wiring ANTES de expandir famílias
Nova evidência EC-00: build_run_adoption_owner configura readback_fn=None e anexa _readback_fns sem uso por DurableRunAdoptionOwner.can_readback/readback. Corrigir wiring das funções por primitiva de maneira contratual, manter fail-closed e testar mutation/no-readback/negative readback, no duplicate effect. Este P0 precede P0.4 e explica potencialmente ausência de reuse independentemente de Laya ou níveis de mineração. Não promover Browser/Trello apenas por verificação de URL/estrutura.
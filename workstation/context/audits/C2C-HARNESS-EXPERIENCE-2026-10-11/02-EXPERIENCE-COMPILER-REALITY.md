# Diagnóstico causal — por que o compilador raramente aparece em uso
Auditoria estática do checkout 9fffa7f; não representa medição de taxa real de promoção no artifact store do usuário.

## Achados comprovados pelo código
EC-01 [ALTA, CONFIGURAÇÃO]: workstation/experience_compiler/compilability_monitor.py:210–253 define mode SHADOW por padrão e requer qualificação válida para DIRECT. workstation/integrations/hermes/run_local_adoption.py:187–195 retorna sem adotar se não DIRECT. Logo, ausência de reutilização automática é consistente com uma instalação que não fez qualificação explícita; configuração efetiva do usuário ainda não foi lida, portanto não atribuir diagnóstico individual categórico.

EC-02 [ALTA, SINAL DE SUPERVISÃO]: workstation/integrations/hermes/tool_observer.py:42–78 produz outcome observed para leitura e uncertain para mutações; workstation/experience_compiler/compiler.py:70–90 requer VERIFIED_SUCCESS. Fluxo de captura por si só não fornece exemplos positivos certificados. Aceitação canônica em corpus.py:49–122 pode elevar amostras elegíveis após conclusão real.

EC-03 [ALTA, COLD START]: workstation/operational_kernel.py:506–532 emite verified_transition quando executa capabilities já compiladas. Isso é bom feedback de reuse, mas não substitui observações verificadas de tarefas inicialmente executadas pelo agente. Verificar quantos fluxos comuns passam por accept_run.

EC-04 [MÉDIA, GATE DE ENTRADA]: compilability_monitor.py:639–656 requer repetição/sucesso para prefilter ou evento especial. Laya só minera se retornar MINE_CANDIDATE ou POSSIBLE_RUN_LOCAL_REUSE: linhas 602–637. Decisões KEEP_COLLECTING, timeout ou abstenção não devem ser interpretadas como falha do compilador sem telemetria.

EC-05 [MÉDIA, LIFECYCLE]: workstation/kanban.py:413–451 efetivamente liga accept_run -> mine -> process_candidate. Logo, NÃO declarar que o coordinator está desintegrado apenas por ler documentos históricos que dizem isso; o teste de produção ainda deve demonstrar que tipos reais de tarefas chegam ao owner Kanban.

EC-06 [MÉDIA, LIMITES]: monitor.py:293–294 tem max_compile_attempts_per_segment=3 e max_validation_attempts=3; :627 corta validações por candidato. Conferir checkpoints :437–509: reidratação existe, mas é preciso testar o comportamento após revisão de evidência e reinício, não assumir retries adaptativos.

EC-07 [MÉDIA, SUPERFÍCIE]: captura e métricas são internas; ausência de UI de capacidades pode reduzir visibilidade sem implicar execução zero. Não há nesta rodada evidência de uma página end-user que apresente funil completo e recibos de reused+VERIFIED.

EC-08 [ALTA, CANÁRIO]: lifecycle.py:466+ tem create_local_canary_validation_provider para famílias de arquivo, registrado quando build_run_adoption_owner ocorre (:174–180). A implementação escreve/lê sondas no sandbox e produz positivo/negativo; antes de reputá-la verificador geral, testar se a sonda discrimina o comportamento de passos específicos da candidata e se todos os contratos/provas são independentemente conferidos. Não estender automaticamente a Browser/Trello.

## O que já melhorou em relação a documentos históricos
Process_event() em SHADOW registra shadow decision mas CONTINUA para preparação de mineração/validação (linhas 602–637). O readback run-local lista atualmente write_file, browser_navigate, browser_snapshot e trello_api_get como suportados, além de read_file. Uma nota anterior que dizia apenas write_file/read_file já está desatualizada. DIRECT exige atestação HMAC válida; não basta string não vazia.

## Verificações falsificáveis prioritárias
A. Extrair contadores reais do monitor: events_seen, filtered, decisions, mining_attempts, candidates_yielded, validation_denials, offers_created, adoption_denials, reused_verified, para TaskRuns específicos.
B. Configuração efetiva, sem exibir segredo: enabled, requested mode, effective mode, downgrade_reason, provider, qualificação e famílias permitidas.
C. Cruzar corpus/provenance com run_closure/owner receipts: taxas de samples observed/uncertain/VERIFIED_SUCCESS; distinguir capacidade descoberta e promovida.
D. E2E com 3 operações equivalentes, 4ª pendente, real owner/readback, recusa de authority, lease ou drift; nenhuma mutação do usuário durante replay.
E. Testar reinício e novo evidence digest sem perda de candidatos/negações.
F. Medir redução REAL de chamadas LLM por outcome VERIFIED, com métricas de provider.

## Veredito
Não há base para afirmar que o compiler está ausente ou inutilizado. Há múltiplas barreiras demonstráveis entre captura e reutilização, e a execução DIRECT não é comportamento default. Melhorar o número de eventos sem reforçar verificação e roteamento tende a aumentar ruído. Hipótese dominante: funil de evidência e de admissão, não falta de um novo compilador.

## EC-00 — Defeito direto de wiring no readback de adoção [P0, REPRODUZÍVEL POR INSPEÇÃO ESTÁTICA]
Fonte MAIN confirmada pelo GitHub (a2b56db1):
- workstation/integrations/hermes/run_local_adoption.py:162–172 cria readback_fns, constrói DurableRunAdoptionOwner(readback_fn=None, readback_primitives=_READBACK) e só depois atribui owner._readback_fns = readback_fns.
- workstation/run_adoption.py:456–463: can_readback verifica self._readback is not None; readback invoca somente self._readback.
- workstation/run_adoption.py:235–247: passos com effects e sem can_readback são rejeitados como readback_unavailable:primitive.

Essa combinação implica can_readback=False para todo primitive do owner construído por build_run_adoption_owner, salvo código não localizado que modifique explicitamente self._readback (busca por _readback_fns no workstation encontrou apenas atribuição e criação). Pode bloquear mutações aprendidas mesmo com DIRECT/offer. Não basta anexar funções num atributo paralelo. Não sugerir remover gate: conectar dispatcher de callbacks por interface canônica e verificar independent readback por primitive, com testes negativos. Atenção adicional: _readback_browser_snapshot usa o raw do próprio snapshot e _readback_trello_api_get checa forma/id dos campos, não necessariamente readback independente da propriedade esperada. Exigir prova semântica por owner antes de incluir família mutativa.

### Por que os testes existentes podem não detectar EC-00
workstation/tests/test_online_compilability_safety.py:115–124 constrói DurableRunAdoptionOwner DIRETAMENTE com readback_fn=self.readback e injeta esse owner no agente. Esse teste contorna a factory build_run_adoption_owner que passa readback_fn=None. Portanto resultado verde desse teste não provaria o wiring de produção. Criar fixture sem _run_adoption_owner injetado, usar factory real e validar callback.

### EC-09 — cache de owner sem chave explícita de TaskRun [HIPÓTESE DE RISCO]
run_local_adoption.py:139–158 verifica task_id/run_id mas retorna _run_adoption_owner cacheado do agente sem comparar esses IDs; closure dispatch criada depois captura task_id. Buscar invalidação externa; não foi localizada por busca literal de _run_adoption_owner fora da factory e do teste. Em mudança de run na mesma instância de agente, isso pode reutilizar owner ligado ao task_id antigo. Não afirmar side effect cross-run sem E2E; exigir teste de troca de TaskRun e reconstrução com fresh identity/authority.
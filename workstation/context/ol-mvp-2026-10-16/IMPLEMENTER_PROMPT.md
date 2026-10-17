# Prompt plug-and-play — IA implementadora Hermes OL-MVP V2 (ARQUIVO HISTÓRICO DE P0)

**SUPERSEDIDO EM P1:** O P0 in-flight já está integrado na branch do PR draft #92; para continuar agora consulte [P1_IMPLEMENTER_PROMPT.md](P1_IMPLEMENTER_PROMPT.md). Não reimplementar o circuito P0, não repetir fases red/green, salvo regressão causal encontrada no P1. O primeiro smoke Electron falhou em boot e o código novo da branch P1 diagnostica e testa 3 cartões em DOM Chromium local.

## Prompt original P0 preservado para rastreabilidade

Voce vai IMPLEMENTAR em kevynlucasprofissional-stack/hermes-agent a aprendizagem operacional autonoma durante a propria TaskRun. NAO redesenhar arquitetura e NAO fazer novo questionario.

## Preparacao
1. Conferir branch, HEAD, git status e files alterados no checkout C:\Github\hermes-agent. Em 16/10 era docs/oneclick-bootstrap-reliability-20261016@73a1ca3, com arquivos nao rastreados de dogfood; preservar tudo. Criar branch propria baseada em HEAD limpo apropriado; jamais merge direto na main.
2. Ler apenas estes quatro arquivos: workstation/context/ol-mvp-2026-10-16/{IMPLEMENTATION_PLAN,PATCH_MAP,DECISIONS,IMPLEMENTER_PROMPT}.md
3. Inspecionar SOMENTE: workstation/{batch_runner,task_compiler,run_adoption,procedure_trace}.py; workstation/integrations/hermes/{run_local_adoption,operational_resolution}.py; workstation/experience_compiler/{compilability_monitor,accepted_observer,progressive}.py. Recuperar outros arquivos so se testes demonstrarem dependencia.

## Execucao em ordem, sem saltos
P0.1 BASELINE — Rodar os testes existentes de online compilability, in-flight handoff, native browser experience e current command resolution; registrar stdout, exit status e causas.
P0.2 RED — Criar workstation/tests/test_ol_mvp_inflight_boundary.py: tres WorkItems, callback apos item1 conclui item2 no store, worker nao executa item2; verificar contagens. Testar callback ausente e callback com excecao.
P0.3 GREEN — Aplicar exatamente PATCH_MAP.md em workstation/batch_runner.py: callback opcional entre itens + refetch em cada iteracao. Rodar teste do P0.2 e regressao batch.
P0.4 WIRING — Conectar com contexto REAL, NAO fabricado, na chamada de DurableBatchRunner.execute_batch realizada por TaskCompiler. Usar workstation_run_local_checkpoint(context) existente em mesma TaskRun e sob owner autorizado. Se necessario ContextVar opcional so para callback. Nao serializar agent nem usar payload LLM como autoridade. Manter checkpoint pre-reasoning existente; nao criar segundo executor.
P0.5 LEARNING — Assegurar notify_canonical_acceptance -> monitor -> candidate -> validator -> AdoptionOffer -> checkpoint -> RunLocalAdopter -> readback independente. Nao forcar DIRECT por config fake. Monitor assincrono; nao adicionar polling ilimitado. Item normal prossegue se oferta ainda nao estiver pronta.
P1.1 NATIVE — Smoke Google -> YouTube na mesma sessao Electron sem SUPERSEDED; browser Trello num quadro descartavel SOMENTE LEITURA com 3+ itens equivalentes, usando DOM vivo. Provar que primeiro ensina e proximo elegivel reutiliza. Se inviavel, relatar NOT_VERIFIED e causa.
P1.2 PERSISTENCIA — Nova TaskRun encontra a mesma capacidade por registro/TaskCompiler com outro input, sem reconstruir cada passo via LLM; readback e necessario.
P2 TELEMETRIA — Comparar adaptive vs compiled: chamadas LLM reais, tokens, custo conhecido, latencia, verificacao, custos do aprendizado e economia liquida; valores ausentes = null. Nunca confundir reducao de ferramentas com economia monetaria.
P3 POSTERIOR — So depois do ciclo P0/P1 comprovado: selecao multimétodo BM25+embedding opcional+LAYA+LLM fallback, memoria hierarquica, versoes dinamicas, quatro ImprovementRuns, fila economica e SourceResearchRun supervisionada.

## Rodar ao menos
python -m pytest -q workstation/tests/test_ol_mvp_inflight_boundary.py
python -m pytest -q workstation/tests/test_online_compilability_safety.py workstation/tests/test_in_flight_handoff.py workstation/tests/test_h080b_native_browser_experience_loop.py workstation/tests/test_current_command_resolution.py
python -m pytest -q workstation/tests/test_browser_batch_actions.py workstation/tests/test_trello_concurrent_edit_protection.py
git diff --check

## Nao executar
Nao copiar antigo explicit_seed.py; nao promover candidato por ACK ou validator local; nao fabricar readbacks, lease ou artefatos; nao ligar DIRECT sem qualificacao; nao repetir efeitos incertos, nem sobrescrever intervencao humana; nao construir novo Browser, engine, registry, scheduler UI ou quatro executores; nao aumentar limite de gastos autonomamente. Nada de merge em main.

## Saida obrigatoria
Branch/HEAD SHA, arquivos alterados e pontos de integracao; suite RED->GREEN com numeros REAIS, resultado do Electron, prova do item1->item2->nova TaskRun, eficiencia liquida com metodo/limites, regressao e riscos. Nao chamar de DONE se teste nativo nao passou. Entregar implementacao, nao outro plano.

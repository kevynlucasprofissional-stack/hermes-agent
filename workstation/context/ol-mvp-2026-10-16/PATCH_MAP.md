# Patch V2 — checkpoint seguro entre itens + reconciliacao duravel
Fonte auditada: main em 16/10/2026. P0a JA APLICADO em workstation/batch_runner.py na branch docs/ol-mvp-inflight-learning-20261016 e verificado por 3 testes novos + 52 regressões. P0b wiring owner e produto Electron AINDA NAO IMPLEMENTADOS/QUALIFICADOS.

## Mudanca 1: workstation/batch_runner.py
Na assinatura DurableBatchRunner.execute_batch, apos guardrails: Any | None = None, inserir parametro:
    on_safe_item_boundary: Optional[Callable[[WorkItem], None]] = None,

Imediatamente apos for item in work_items:, adicionar:
    item = self.store.get_item(item.id)
A lista work_items foi obtida ANTES da iteracao. Um adotador pode completar itens pendentes no store apos o item anterior; sem refetch, o worker pode repetir efeito externo.

Apos processar guardrails e ANTES de if anomalies and stop_on_exception:, inserir:
    if item_success and on_safe_item_boundary is not None:
        try:
            on_safe_item_boundary(self.store.get_item(item.id))
        except Exception:
            logger.warning("Optional run-local learning checkpoint failed", exc_info=True)

Hook apenas de notificacao entre itens, fora de efeito em voo; nao garante VERIFIED externo, nao altera policy nem executa por si. Pode nao disparar em todos os fluxos: investigar apenas o pipeline da TaskRun piloto. Se estado obsoleto/deletado, negar de modo seguro.

## Mudanca 2: wiring com OWNER REAL
workstation/task_compiler.py invoca runner.execute_batch no bloco de execucao. workstation/integrations/hermes/run_local_adoption.py ja fornece workstation_run_local_checkpoint(context) que exige agent e a TaskRun canonica. Essa funcao ja esta no pre-reasoning em operational_resolution.py.

A IA implementadora DEVE localizar invocador trusted de TaskCompiler; passar callback IN-MEMORY, nao via request JSON, obtendo context.agent autêntico. Se necessario adicionar ContextVar separada ao execution_context; nao alterar posicoes dos componentes da tupla _dispatch_context nem criar fake agent/lease. Callback nao deve recursar quando proprio RunLocalAdopter executar itens.

## Testes RED->GREEN
- WorkItems 1,2,3. Callback apos 1 marca 2 COMPLETED via store. Worker precisa executar SOMENTE 1,3; summary.completed = 3.
- Sem callback, comportamento existente identico.
- Falha na callback registra warning sem interromper tarefa principal.
- Nao executar com lease revogado, incerteza anterior, drift, alteracao humana concorrente.
- E2E: evento de readback aceito -> monitor -> oferta qualificada -> runtime checkpoint -> proximo item elegivel sem System-2 -> readback externo. Nunca fabricar VERIFIED.

## Riscos e NAO-Fazer
Monitor e assincrono; uma oferta pode chegar tarde. Nao bloquear o batch em sleep arbitrario. SHADOW por padrao; DIRECT exige qualificacao legitima. browser_console opaco nao pode ser promovido diretamente. O antigo explicit_seed.py e explicit_replay.py sao desvios do objetivo imediato.

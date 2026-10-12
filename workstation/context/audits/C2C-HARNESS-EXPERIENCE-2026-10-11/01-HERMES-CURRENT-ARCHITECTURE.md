# Arquitetura efetiva do Hermes e proveniência
Baseline local 9fffa7f3ffcc; main a2b56db1bc9e. Evidência principal obtida por leitura do código local, contrastada para pontos críticos com GitHub main.

## Ownership por plano
- Interação/ferramenta: workstation/integrations/hermes/tool_observer.py, linhas 27–117; captura progressiva somente quando dispatched e durable_execution_active, sob task/run presentes.
- Amostra: workstation/experience_compiler/progressive.py, linhas 10–23; converte primitive/route/outcome e estado abstrato para TransitionSample e chama ExperienceCorpus.capture.
- Corpus: workstation/experience_compiler/corpus.py, accept_run (aprox. linhas 49–124); só converte o último candidato de uma run em VERIFIED_SUCCESS diante de outcome VERIFIED_COMPLETED, ausência de uncertain_mutation e recibos efetivamente associados.
- Compilador: workstation/experience_compiler/compiler.py, compile (70 em diante) exige sucesso verificado, efeito semântico estável, segmentação, generalização e causalidade.
- Monitor Laya: workstation/experience_compiler/compilability_monitor.py, process_event (581 em diante), mineração run-local (721), validação (751) e ofertas DIRECT (786).
- Validação canário: workstation/experience_compiler/lifecycle.py, create_local_canary_validation_provider (466 em diante).
- Admissão run-local: workstation/integrations/hermes/run_local_adoption.py, checkpoint (187–212), owner de execução e readback por primitiva.
- Fronteira pré-System-2: workstation/integrations/hermes/operational_resolution.py, linhas 274–295; primeiro tenta Prefab Fast Path, depois checkpoint de adoção, depois resolução normal.
- Ciclo pós-commit: workstation/kanban.py, linhas 413–451; ExperienceCorpus.accept_run, ExperienceCompiler.mine e ExperienceValidationPromotionCoordinator.process_candidate em caminho real de conclusão.
- Execução de capability: workstation/operational_kernel.py, linhas 485–541; captura eventos e telemetria quando uma capacidade já está sendo executada.
- Formato/persistência: workstation/operational_capabilities.py, OperationalCapability e Registry; dados executáveis estruturados, não SKILL.md.
- Dispatcher/policy/verification: workstation/control_plane/{router,dispatcher,verification}.py, workstation/run_adoption.py e workstation/run_closure.py. Não são substituídos por visualizador.

## Call graph auditável
User turn -> turn admission/TaskRun -> pre-reasoning operational_resolution -> prefab match -> run-local checkpoint (somente DIRECT com offer) -> LLM/tool fallback -> tool_observer -> capture_progressive -> corpus artifact -> notify_online_compilability -> monitor prefiltro/Laya -> scoped mine -> run-local validate/offer -> próximo checkpoint do mesmo TaskRun -> RunLocalAdopter -> dispatcher/readback. Em paralelo, conclusão canônica do Kanban -> accept_run -> mine global -> coordinator -> promotion policy -> registry -> router/OperationalKernel em novas tarefas.

## Pontos importantes
SHADOW não é mais retorno antecipado: process_event() agora permite mineração preparatória em qualquer modo quando o estágio da decisão determina. Entretanto ready_offers() e checkpoint exigem DIRECT; load_learning_policy() escolhe SHADOW por padrão. Sem atestação HMAC válida, pedido DIRECT cai para SHADOW.

O observador genérico não transforma resultado de tool em VERIFIED_SUCCESS: read_effects -> observed; mutação -> uncertain, salvo falha classificada. O caminho de aceitação posterior e o OperationalKernel são owners distintos das evidências verificadas.

## Limitações
Não foi demonstrado, nesta auditoria, um E2E com modelo Laya real, certificado, replay independente e adoção no mesmo TaskRun. Não confundir caminhos existentes com certificação produtiva.

## Contradição owner de readback (P0)
run_local_adoption.py:162–172 fornece readback_fn=None e owner._readback_fns, mas run_adoption.py:456–463 acessa exclusivamente self._readback. O plan_item_adoption bloqueia efeitos sem can_readback (:243–244). Essa é uma desconexão concreta entre factory e protocolo de owner. Uma UI que apresentasse capacidades como prontas sem refletir essa negação seria enganosa.
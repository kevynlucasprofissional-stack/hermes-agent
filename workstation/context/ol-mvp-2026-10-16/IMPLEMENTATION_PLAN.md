# OL-MVP V2 — Aprendizagem operacional dentro da TaskRun
Data: 2026-10-16 | Status: PLANEJADO, NAO QUALIFICADO | Prioridade: P0, foco 80/20

## Objetivo
Aprender autonomamente com o item 1, compilar a capacidade candidata a partir de evidencia independente, reutilizar no proximo item elegivel ainda NA MESMA TaskRun e executar os demais itens sem redescoberta por LLM. Preservar autoridade, lease, estado duravel, verificacao e conclusao integral da tarefa. Depois provar persistencia em outra TaskRun e economia liquida.

## Evidencia de dogfood
Auditoria de 16/10: 56 exports JSON de sessao, 10 HTMLs e 40 documentos de contexto (inventario, nao 56 execucoes independentes). open-trello-20261009 teve repeticao, handoffs e sobrescrita de edicao humana; abrir-google-20261012 abriu Google facilmente mas o segundo turno teve SUPERSEDED. HTMLs Trello sao fixtures, nao DOM vivo. BAV03/BAV04/BAV05 mostram viabilidade experimental limitada. E2E Windows Electron de adocao progressiva continua NAO COMPROVADO. Nao inferir USD por quantidade de mensagens.

## Codigo atual a REUTILIZAR
- workstation/experience_compiler/compilability_monitor.py: SHADOW padrao; DIRECT condicionado a atestacao; eventos, ofertas e checkpoints.
- workstation/experience_compiler/{accepted_observer,progressive,compiler,compilability_validation}.py: evidencia aceita, corpus, candidatos e validacao.
- workstation/run_adoption.py: RunLocalAdopter, AdoptionOffer, run owner, lease, efeito e readback.
- workstation/integrations/hermes/run_local_adoption.py: workstation_run_local_checkpoint.
- workstation/integrations/hermes/operational_resolution.py: checkpoint previo ao raciocinio (ja existente).
- workstation/batch_runner.py: DurableBatchRunner.execute_batch; iteracao materializada de itens.
- workstation/task_compiler.py: execution_context e invocacao de execute_batch.
- workstation/procedure_trace.py: browser_console opaco nao admite replay automatico.
- workstation/{operational_capabilities,operational_kernel,memory,routines}.py e telemetry/: catalogo, execucao, memoria e metricas existentes.

## P0 Gate 0 — linha de base curta
Verificar HEAD, branch, git status, modificacoes do usuario e testes presentes. Rodar tests de online compilability, in-flight handoff, browser experience e current command; registrar resultados. Sem criar outro motor ou reescrever o sistema.

## P0 Gate 1 — fronteira ENTRE itens (prioridade maxima)
A inspeção do codigo main 16/10 achou checkpoint run-local na fronteira pre-raciocinio, mas nao no fechamento do item do DurableBatchRunner. Patch minimo detalhado em PATCH_MAP.md:
1) executar callback opcional depois da conclusao persistida e das guardrails;
2) reconsultar WorkItem no store no inicio de cada iteracao, pois adotador pode ter concluido o proximo item enquanto a lista inicial esta obsoleta;
3) ligar callback apenas pelo owner confiavel com agent e TaskRun canonicos, em memoria, sem passar identidade do modelo pelo payload;
4) nao bloquear espera de worker assincrono, nao supor que oferta ja exista no segundo item;
5) nunca transformar validacao local isolada em VERIFIED externo.

Aceite: primeiro item humano/LLM gera amostra VALIDADA REAL; monitor produz oferta qualificada; runtime no boundary adota proximo item elegivel; persistencia readback; proximo item nao e executado duas vezes. Se faltar evidencia, NOT_VERIFIED, sem contornar gate.

## P1 — demonstracao produto
Smoke Google -> YouTube mesmo chat sem SUPERSEDED; Trello em ambiente de teste SOMENTE LEITURA com tres itens equivalentes sobre DOM vivo. Nova TaskRun recupera capacidade para parametros diferentes; comparacao com baseline adaptativo. Somente depois editar em quadro descartavel com protecao de versao/alteracao humana, efeito incerto sem replay.

## P2 — evolucao e metrica
Manter versoes recuperaveis, identidade logica compartilhada e promocao global otimista so depois de verificação inicial/contrato; repair seletivo, rollback contextual. Medir chamadas reais System-2, tokens, preco verificado, tempo, sucesso, custo de aprendizagem, manutencao e reuso. Separar economia bruta de economia LIQUIDA e de valor estrategico. 95% sucesso e 50% custo menor: metas de avaliacao, nao resultados.

## P3 — direcao consolidada, FORA DO BLOQUEIO P0
Memoria universal hierarquica com compilacao seletiva; telemetria independente. Selecao multimétodo: exato/contrato -> BM25/embedding opcional -> LAYA/System-1 conforme ambiguidade -> Router+Policy -> LLM/System-2 para novidade. Aprender a se abster e compor. Quatro especialidades SkillImprovementRun, CapabilityImprovementRun, SourceResearchRun, SelectionImprovementRun sobre infraestrutura comum, filas persistentes, agendamento e orçamento global com limites imutaveis do usuario. SourceResearchRun investiga e testa isolado, NUNCA altera codigo operacional sem autorizacao explicita.

## Gates nao negociaveis
Lease e autoridade sao do runtime; nao fabricar provas e nao forcar DIRECT. Efeito externo requer readback independente e controle de duplicacao. Nao sobrescrever edicoes humanas. Nao usar browser_console opaco como macro arbitraria. Nao gravar segredos em memoria. Nao implementar n8n, outro Browser, outro registry, editor de workflow ou quatro executores.

## Entrega
Branch/commit, arquivos mudados, testes RED->GREEN, logs nativos quando houver, comprovacao de item 1->item 2->TaskRun nova, metricas reais ou null, riscos pendentes. Nao merge na main sem autorizacao.

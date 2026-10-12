# Conclusões — Hermes Work, Agent Harness, Experience Compiler
**Veredito: priorizar valor observável e verificável do compilador existente; visualizar primeiro, editar depois.**
Base: checkout local HEAD 9fffa7f e GitHub main a2b56db; 18 referências, 147.365 arquivos inventariados com exclusões declaradas, 55 sessões de dogfood agregadas. A análise de código foi DIRECIONADA, não leitura semântica integral de 121.884 arquivos. Nenhum teste pytest reexecutado: módulo não instalado no Python 3.14 local consultado.

## Descobertas demonstradas
1. Monitor já realiza mineração preparatória em SHADOW quando Laya propõe estágio elegível (compilability_monitor.py:602–637). Logo, documentos que dizem que SHADOW impede *qualquer* mineração estão desatualizados.
2. Admissão/effects run-local só avançam em DIRECT com HMAC attestation válida e offer (compilability_monitor.py:786+, run_local_adoption.py:187+). Não é o default: SHADOW é padrão (compilability_monitor.py:210–253).
3. Captura genérica marca reads observed e mutações uncertain, não VERIFIED_SUCCESS (tool_observer.py:42–78). O compile exige exemplos finais verificados (compiler.py:70–90); accept_run é um caminho separado com recibos vinculados (corpus.py:49–122).
4. A conclusão normal do Kanban chama accept_run, mine e process_candidate (kanban.py:413–451). Portanto o ciclo NÃO é apenas fixture; falta medir cobertura real desse caminho na experiência cotidiana.
5. Provedor de canário filesystem está implementado (lifecycle.py:466+) e registrado pelo owner run-local. Requer validação adversarial de que sonda positiva/negativa é discriminativa de candidata, e não meramente de scratch I/O.
6. N8n e Activepieces possuem motor, representação visual e versionamento próprios; Activepieces oferece FlowVersion DRAFT/LOCKED e layout de loops/branches no flow-canvas-util. Proposta: reutilizar ideias de representação, não motor inteiro.
7. Referências Ratchet, Voyager, FlowEvo, Trace2Skill e memorizz oferecem retrieval, evolução, summaries e observabilidade complementares; nenhuma substitui formal verification/effect authority de Hermes nos trechos analisados.
8. Dogfood: 55 sessões, 14.688 mensagens, 8.064 ferramentas. Open Trello 470 ferramentas, com 180 browser_console. Não equivale a custo/LLM calls; repetir ferramentas não garante closure semântica.

## Ranking para decidir agora
P0 — funil rastreável com sinais VERIFIED -> candidate -> validation -> run-local offer -> reused verified; qualificação REAL pequena.
P1 — guardrails/counters e Capability Explorer READ-ONLY, além de redução de consultas Browser medidamente redundantes.
P2 — editor de parâmetros e grafo limitado que cria versões candidatas imutáveis, sem herdar PROMOTED.
P3 — workflows gerais só depois de validar semântica de branches/loops/schedules e ROI sem duplicar executor.

## O que manter
OperationalCapabilityRegistry, ExperienceCompiler/Corpus, ExperiencePromotionPolicy, OperationalKernel, TaskRun, control_plane/verification e leases. Não confundir inclusão de n8n/LangGraph com produto melhor; a arquitetura atual de autoridade já tem contratos que essas referências não foram demonstradas como capazes de substituir.

## O que NÃO fazer
- Forçar promotion por frequência.
- Considerar dados OBSERVED como prova positiva.
- Habilitar DIRECT sem atestação/canonical policy.
- Copiar código do n8n Sustainable Use ou memorizz Noncommercial presumindo licença permissiva.
- Implementar UI visual antes de corrigir descoberta/adoção do compiler.
- Declarar testes verdes apenas porque documentação histórica contém logs de aprovação.

## Próxima execução
O documento 09-IMPLEMENTATION-HANDOFF.md descreve commits-alvo, patches mínimos e gates. Este conjunto é um handoff de auditoria parcial com evidências de código. Exige etapa adicional de revisão detalhada do corpus/telemetria do dispositivo e E2E Electron para certificar as causas no uso produtivo e cumprir integralmente todas as exigências do prompt original.

## Correção da prioridade máxima: readback indisponível por construção
Identificado posteriormente na auditoria, no código publicado e no local, um bloqueio concreto: run_local_adoption.py cria mapa _readback_fns mas passa readback_fn=None a DurableRunAdoptionOwner, enquanto run_adoption.py.can_readback só considera self._readback. Isso pode bloquear TODOS os passos effectful via readback_unavailable, mesmo que estejam habilitados DIRECT, validados e admitidos. Revisar antes de ampliar Laya ou implantar editor visual. A conclusão é estática, não um teste E2E executado.

**Diagnóstico de cobertura:** o teste de segurança atualmente injeta owner customizado com callback positivo em test_online_compilability_safety.py:115–124. Isso explica como suites podem passar enquanto a factory de produção fica desconectada. Outro risco a investigar é cache de _run_adoption_owner sem chave task/run em run_local_adoption.py:139–146; requer E2E antes de classificação como bug funcional.